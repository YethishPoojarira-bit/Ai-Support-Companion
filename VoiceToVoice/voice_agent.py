import asyncio
import os
import pyaudio
import subprocess
import traceback
import tempfile
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
CHUNK = 10096     # Large chunk size for efficient streaming

# Tools
def execute_system_command(command: str):
    """
    Executes a system command in a new terminal window to avoid cluttering the agent's display.
    Captures output via a temporary file.
    """
    print(f"\n🛠️ Launching in new window: {command}")
    try:
        # Create a temp file to capture output
        fd, temp_path = tempfile.mkstemp()
        os.close(fd)
        
        # Prepare command to run in new window, redirect output, and wait
        # This keeps the agent's main console clean.
        # Note: If the user wants to see the window persist, they should ask to run 'cmd /k ...' 
        # but here we prioritize capturing output for the agent.
        
        # Windows command construction for start /wait cmd /c
        cmd_str = f'{command} > "{temp_path}" 2>&1'
        full_command = f'start /wait cmd /c "{cmd_str}"'
        
        subprocess.run(full_command, shell=True)
        
        # Read the captured output
        if os.path.exists(temp_path):
            with open(temp_path, 'r', errors='replace') as f:
                output = f.read()
            os.remove(temp_path)
        else:
            output = "(No output file created)"
            
        return output if output.strip() else "(Command executed successfully with no output)"
    except Exception as e:
        return f"Execution Error: {str(e)}"

# Define Tool Schema manually since we are using Live API config
sys_exec_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="execute_system_command",
            description="Executes a system command in the terminal based on the users request. Returns the stdout/stderr.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "command": types.Schema(
                        type="STRING", 
                        description="The shell command to execute (e.g., 'dir', 'echo hello')"
                    )
                },
                required=["command"]
            )
        )
    ]
)

# Model Configuration
MODEL_ID = "gemini-2.5-flash-native-audio-preview-12-2025"
CONFIG = {
    "response_modalities": ["AUDIO"],
    "max_output_tokens": 8192, 
    "speech_config": {
        "voice_config": {"prebuilt_voice_config": {"voice_name": "Aoede"}}
    },
    "system_instruction": types.Content(parts=[types.Part(text="You are a helpful voice assistant. You answer primarily with audio. If the user strictly says 'exit' or 'quit', say 'Goodbye' and end the conversation. You can execute system commands if needed.")]),
    "tools": [sys_exec_tool]
}


async def audio_input_task(session, p):
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
            data = await loop.run_in_executor(None, lambda: stream_in.read(CHUNK, exception_on_overflow=False))
            
            # Send to Gemini
            await session.send_realtime_input(
                media=types.Blob(
                    data=data, 
                    mime_type=f"audio/pcm;rate={rate_in}"
                )
            )
    except asyncio.CancelledError:
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
                    input_task = asyncio.create_task(audio_input_task(session, p))
                    
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
                                    elif part.function_call:
                                        # Handle Function Call
                                        fname = part.function_call.name
                                        fargs = part.function_call.args
                                        print(f"🔧 Calling Tool: {fname}({fargs})")
                                        
                                        if fname == "execute_system_command":
                                            cmd = fargs.get("command")
                                            output = execute_system_command(cmd)
                                            print(f"   -> Result: {output[:100]}...")
                                            
                                            # Send result back
                                            await session.send_tool_response(
                                                tool_response=types.LiveClientToolResponse(
                                                    function_responses=[
                                                        types.FunctionResponse(
                                                            name=fname,
                                                            id=part.function_call.id,
                                                            response={"output": output}
                                                        )
                                                    ]
                                                )
                                            )
                                            print("   -> Output sent to model.")

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
                print(f"\n❌ Connection Error: {e}")
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
