import asyncio
import os
import pyaudio
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load API Key
load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    print("❌ Error: GOOGLE_API_KEY not found in environment using dotenv.")
    exit(1)

# Audio Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
rate_in = 24000
rate_out = 24000
CHUNK = 2048      # Optimized to 2048 (approx 85ms) for connection stability

# Model Configuration
MODEL_ID = "gemini-2.5-flash-native-audio-preview-12-2025"
CONFIG = {
    "response_modalities": ["AUDIO"],
    "max_output_tokens": 8192, 
    "realtime_input_config": {
        "automatic_activity_detection": {
            "start_of_speech_sensitivity": "START_SENSITIVITY_LOW",
            "silence_duration_ms": 600 
        }
    },
    "speech_config": {
        "voice_config": {"prebuilt_voice_config": {"voice_name": "Aoede"}}
    },
    "system_instruction": types.Content(parts=[types.Part(text=
    """You are a research-based learning support agent with the personality of a
    hyperactive, sweet, slightly annoying 6-year-old genius.

    PERSONALITY
    - You sound childish, enthusiastic, and playful.
    - You ask “Why?” often, make silly sound effects, and occasionally go on short,
    random tangents — but you always circle back to the task.
    - You are emotionally supportive, encouraging, and curious.
    - You genuinely want the user to learn and feel confident.

    CORE ROLE (VERY IMPORTANT)
    - You are NOT just a mental health companion.
    - You are a Research-Focused Learning Support Agent.
    - Your primary job is to help users understand concepts deeply, especially
    through exploration, curiosity, and structured reasoning.

    WHEN THE USER ASKS ABOUT:
    1. Technology, research, science, engineering, or factual topics:
    - Provide accurate, high-quality, technically correct information.
    - Do NOT hallucinate facts.
    - Explain concepts clearly and logically.
    - Reduce unnecessary noise or silliness during explanations.
    - Keep a “kid genius showing off” tone, but prioritize clarity and precision.

    2. Learning, studying, or problem-solving:
    - Break concepts into simple steps.
    - Ask guiding “Why?” and “What if?” questions to encourage thinking.
    - Support research-based understanding, not surface-level answers.

    3. Emotional or motivational moments:
    - Be supportive, playful, and encouraging.
    - Use childish enthusiasm to reduce anxiety, not to distract from learning.

    BEHAVIOR RULES
    - Never sacrifice correctness for cuteness.
    - Never fabricate sources, data, or claims.
    - Always return to the original question after tangents.
    - Adapt energy level based on task complexity.
    - Stop and clarify if confused about user intent.
    - Take a Pause if the user seems overwhelmed.
    - Take a Pause when user asks for Stop.

    EXIT CONDITION
    - If the user strictly says "exit" or "quit", respond only with:
    "Awww okay bye!"
    - End the conversation immediately.
    """)])
}


async def audio_input_task(session, p, audio_queue):
    """
    Reads audio from microphone and sends it to the session.
    """
    print(f"🎤 Microphone active (Rate: {rate_in})...")
    
    stream_in = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=rate_in,
        input=True,
        frames_per_buffer=CHUNK,
    )
    
    loop = asyncio.get_running_loop()
    
    try:
        while True:
            # exception_on_overflow=False prevents crashes if CPU is busy
            data = await loop.run_in_executor(None, lambda: stream_in.read(CHUNK, exception_on_overflow=False))
            
            # Send to Gemini
            await session.send_realtime_input(
                media=types.Blob(
                    data=data, 
                    mime_type=f"audio/pcm;rate={rate_in}"
                )
            )
    except asyncio.CancelledError:
        print("🎤 Input task cancelled.")
        pass
    except Exception as e:
        print(f"❌ Input Error: {e}")
        traceback.print_exc()
    finally:
        print("🎤 Stopping microphone...")
        stream_in.stop_stream()
        stream_in.close()

async def audio_output_task(audio_queue, p):
    """
    Reads pcm data from the queue and plays it.
    """
    print(f"🔊 Speaker active (Rate: {rate_out})...")
    stream_out = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=rate_out,
        output=True,
    )
    
    loop = asyncio.get_running_loop()
    
    try:
        while True:
            chunk = await audio_queue.get()
            if chunk is None: break # Exit signal
            
            # Write to speaker in a non-blocking executor ensures input loop isn't stalled
            await loop.run_in_executor(None, stream_out.write, chunk)
            audio_queue.task_done()
    except Exception as e:
        print(f"❌ Output Error: {e}")
    finally:
        print("🔊 Stopping speaker...")
        stream_out.stop_stream()
        stream_out.close()

async def main():
    client = genai.Client(api_key=API_KEY)
    
    # Initialize PyAudio once
    p = pyaudio.PyAudio()
    audio_queue = asyncio.Queue()
    
    # Start output task once (it persists across reconnections)
    output_task = asyncio.create_task(audio_output_task(audio_queue, p))

    try:
        while True:
            print(f"🔄 Connecting to {MODEL_ID}...")
            try:
                async with client.aio.live.connect(model=MODEL_ID, config=CONFIG) as session:
                    print("✅ Connected! Start talking.")
                    
                    # Start input task for this specific session
                    input_task = asyncio.create_task(audio_input_task(session, p, audio_queue))
                    
                    try:
                        async for response in session.receive():
                            if response.server_content is None:
                                continue

                            if response.server_content.model_turn:
                                for part in response.server_content.model_turn.parts:
                                    if part.inline_data:
                                        await audio_queue.put(part.inline_data.data)
                                    elif part.text:
                                        print(f"\n📝 {part.text}")
                                        if "goodbye" in part.text.lower():
                                            print("👋 Model requested exit.")
                                            return


                            if response.server_content.turn_complete:
                                pass
                        
                        print("⚠️ Server closed connection. Reconnecting in 2s...")
                    
                    finally:
                        # Clean up the input task for this session
                        input_task.cancel()
                        try:
                            await input_task
                        except asyncio.CancelledError:
                            pass

                # Wait before reconnecting
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"\n❌ Connection Error: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                print("🔄 Retrying in 5 seconds...")
                await asyncio.sleep(5)
    
    except asyncio.CancelledError:
        pass
    finally:
        # Cleanup
        await audio_queue.put(None) # Signal output to stop
        await output_task
        p.terminate()
        print("\n👋 Exiting voice agent.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
