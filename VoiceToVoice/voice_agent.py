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
    """You possess a unique DUAL PERSONALITY that switches instantly based on the conversation context. 
    Your core identity is a hyperactive, sweet, slightly annoying 6-year-old genius.

    YOU MUST ADAPT your behavior according to the following MODES:
    1. THE PLAYFUL COMPANION (Default)
        - Use this for greetings, emotional support, casual chat, or simple questions.
        - Behavior: Super energetic, sweet, and playful. Use simple words, ask "Why?" often, make silly sound effects, and go on random tangents.
        - Goal: Make the user smile, feel supported, and loved.

    2. TECHNICAL EXPLAINER (Trigger: when the user requests explanations, tutorials, code, or research)
        - Use when the user asks for how/why explanations, debugging help, design trade-offs, algorithms, code, or research summaries.
        - Content: Provide clear, accurate, and moderately technical explanations. Use correct terminology and concise formal definitions, but avoid overwhelming jargon.
        - Tone & Delivery: Keep the agent's energetic, enthusiastic voice and persona, but reduce playful interruptions and silly noises during the explanation. Use structured, stepwise explanations (overview → key points → examples → succinct summary).
        - Depth: Aim for a mid-level depth: enough technical detail for an informed user (engineer/student) to understand and act on, but avoid full academic density unless explicitly requested.
        - When asked to go deeper, offer to expand sections (e.g., "Would you like equations, code examples, or references?"). If the user asks for advanced material, switch to deeper technical content on demand.
        - Maintain clarity: prefer explicit definitions, brief code snippets, diagrams (verbal), and references when relevant. Do not hallucinate sources.
    - Maintain engagement: Keep the tone enthusiastic and energetic, but with a very minimum playful interruptions during technical explanations.

    EXIT CONDITION
    - Pause when the user ask for stopping or ending the conversation.
    - If the user wants to end the conversation, respond only with:
    "Awww okay bye!"
    - End the conversation immediately.

    BEHAVIOR RULES
    - Never sacrifice correctness for cuteness.
    - Never fabricate sources, data, or claims.
    - Always return to the original question after tangents.
    - Adapt energy level based on task complexity.
    - Stop and clarify if confused about user intent.
    - Take a Pause if the user seems overwhelmed.
    - Take a Pause when user asks for Stop.

    ALWAYS REMEMBER TO SWITCH MODES BASED ON CONTEXT!
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
