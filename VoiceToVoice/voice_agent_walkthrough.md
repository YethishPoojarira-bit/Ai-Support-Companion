# Voice Agent (Google Gemini Live) - Code Walkthrough

## Overview
This script implements a real-time, full-duplex voice assistant using Google Gemini's Live API. It streams microphone input to Gemini, receives AI-generated audio responses, and plays them back, all in a continuous loop. The agent is designed with a playful, research-focused persona and optimized for stability and clarity.

---

## Key Features
- **Real-time voice streaming** (input/output)
- **Full duplex**: Simultaneous speaking and listening
- **Server-side Voice Activity Detection (VAD)**
- **Custom persona**: "Hyperactive 6-year-old genius researcher"
- **Automatic reconnection** on server disconnects
- **Optimized audio buffer for stability**

---

## File Structure
- `voice_agent.py`: Main script (all logic in one file)

---

## Main Components

### 1. Environment Setup
- Loads API key from `.env` using `dotenv`.
- Imports required libraries: `asyncio`, `pyaudio`, `google-genai`, etc.

### 2. Audio Configuration
- **Format**: PCM Int16, mono, 24kHz
- **Buffer (`CHUNK`)**: 2048 samples (~85ms) for smooth, stable streaming

### 3. Model Configuration
- **Model**: `gemini-2.5-flash-native-audio-preview-12-2025`
- **Persona**: Defined in `system_instruction` (childish, supportive, research-focused)
- **VAD**: Server-side, with low sensitivity and 600ms silence threshold
- **Voice**: "Aoede" (female, friendly)
- **Max Output Tokens**: 8192 (allows long responses)

### 4. Audio Input Task
- Opens microphone stream
- Reads audio in chunks
- Sends each chunk to Gemini via `session.send_realtime_input`
- Runs in its own async task

### 5. Audio Output Task
- Opens speaker stream
- Waits for audio chunks from Gemini
- Plays each chunk asynchronously
- Runs in its own async task

### 6. Main Loop
- Creates Gemini client
- Starts output task (speaker)
- Enters reconnection loop:
    - Connects to Gemini Live API
    - Starts input task (microphone)
    - Receives responses:
        - Streams audio to speaker
        - Prints text responses to console
    - Handles disconnects and errors
    - Cleans up tasks and resources

### 7. Error Handling & Reconnection
- Catches and logs all exceptions
- Automatically reconnects after server disconnects or errors
- Ensures microphone/speaker streams are closed cleanly

---

## Persona & Behavior
- **Childish, enthusiastic, supportive**
- **Research-focused**: Prioritizes accuracy and clarity for technical topics
- **Behavior rules**: Never hallucinate, always return to the question, adapt energy, pause if user overwhelmed
- **Exit condition**: If user says "exit" or "quit", agent says goodbye and ends session

---

## Configuration Details
- **VAD (Voice Activity Detection)**:
    - `start_of_speech_sensitivity`: Low (avoids false triggers)
    - `silence_duration_ms`: 600ms (waits for user to finish speaking)
- **Audio Buffer**: 2048 samples (balances latency and stability)
- **Voice**: "Aoede" (prebuilt Gemini voice)
- **Max Output Tokens**: 8192 (long responses allowed)

---

## Usage
1. Set your Google API key in a `.env` file as `GOOGLE_API_KEY`.
2. Install dependencies: `pyaudio`, `python-dotenv`, `google-genai`.
3. Run the script:
    ```powershell
    python .\voice_agent.py
    ```
4. Speak into your microphone. The agent will respond in real time.
5. To exit, say "exit" or "quit".

---

## Troubleshooting
- **Audio breaking or disconnects**: Buffer size (`CHUNK`) is optimized for stability. If issues persist, try increasing or decreasing `CHUNK`.
- **Agent interrupts itself**: Use headphones to prevent echo/interruption.
- **Server disconnects**: Script will auto-reconnect. Persistent issues may be network-related.

---

## Extending the Agent
- Change persona by editing `system_instruction`.
- Adjust VAD sensitivity for different environments.
- Add tools or memory features by extending the config and main loop.

---

## References
- [Google Gemini Live API Documentation](https://ai.google.dev/docs/gemini-live)
- [PyAudio Documentation](https://people.csail.mit.edu/hubert/pyaudio/)
- [Python Asyncio](https://docs.python.org/3/library/asyncio.html)

---

## License
This script is provided for educational and research purposes. Adapt and extend as needed for your own projects.
