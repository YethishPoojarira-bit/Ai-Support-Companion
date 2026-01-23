 # Voice Agent (Google Gemini Live) — Updated Walkthrough

 This document describes the current state of `voice_agent.py` and the recent changes made during tuning and persona updates.

 ## Summary of Recent Changes
 - `CHUNK` is set to `2048` (approx 85ms) for better connection stability.
 - Server-side automatic VAD is enabled with `start_of_speech_sensitivity: START_SENSITIVITY_LOW` and `silence_duration_ms: 600` (you can adjust this in `CONFIG`).
 - System prompt updated to a dual-personality behavior: a playful companion and a mid-level technical explainer that maintains energetic delivery while reducing silliness during technical answers.
 - Input read uses `exception_on_overflow=False` to avoid microphone crashes when the CPU is under load.
 - Reconnection and error logging were improved for clearer diagnostics.

 ## What this script does
 The script implements a real-time voice assistant that:
 - Streams microphone audio to Google Gemini Live.
 - Receives the model's audio responses and plays them on speakers.
 - Prints any text parts of responses to the console.
 - Reconnects automatically if the server closes the connection.

 ## Important configuration
 - `FORMAT`: `pyaudio.paInt16` (PCM 16-bit)
 - `CHANNELS`: `1` (mono)
 - `rate_in` / `rate_out`: `24000` Hz
 - `CHUNK`: `2048` samples (~85ms)
 - `MODEL_ID`: `gemini-2.5-flash-native-audio-preview-12-2025`
 - `CONFIG` highlights:
     - `response_modalities`: `AUDIO`
     - `max_output_tokens`: `8192`
     - `realtime_input_config.automatic_activity_detection.start_of_speech_sensitivity`: `START_SENSITIVITY_LOW`
     - `realtime_input_config.automatic_activity_detection.silence_duration_ms`: `600`
     - `speech_config.voice_config.prebuilt_voice_config.voice_name`: `Aoede`
     - `system_instruction`: Dual-personality prompt (Playful Companion + Technical Explainer)

 ## Core components (how it works)
 - `audio_input_task(session, p, audio_queue)`
     - Opens the microphone stream and reads PCM chunks.
     - Uses `loop.run_in_executor` to avoid blocking the event loop while reading audio.
     - Sends each chunk to Gemini with `session.send_realtime_input(media=types.Blob(...))`.

 - `audio_output_task(audio_queue, p)`
     - Opens the output (speaker) stream.
     - Awaits audio chunks on an asyncio queue and writes them to the speaker via `run_in_executor`.

 - `main()`
     - Creates the `genai.Client` and global audio objects.
     - Starts a persistent `audio_output_task`.
     - Connects to Gemini in a reconnection loop, starts per-session `audio_input_task`, and consumes `session.receive()`.
     - On server disconnect, cancels the input task and reconnects after a brief sleep.

    ## Diagrams (Mermaid)

    High-level architecture:

    ```mermaid
    flowchart LR
        Mic[Microphone]
        SubgraphInput[audio_input_task]
        SubgraphOutput[audio_output_task]
        Gemini[Google Gemini Live]
        Speaker[Speaker]

        Mic -->|PCM chunks| SubgraphInput
        SubgraphInput -->|realtime input| Gemini
        Gemini -->|audio parts| SubgraphOutput
        SubgraphOutput -->|PCM audio| Speaker
    ```

    Sequence diagram for connection, streaming and reconnection:

    ```mermaid
    sequenceDiagram
        participant Client
        participant Mic
        participant Gemini
        participant Speaker

        Client->>Mic: open stream (audio_input_task)
        Client->>Speaker: open stream (audio_output_task)
        loop streaming
            Mic-->>Client: send CHUNK
            Client-->>Gemini: session.send_realtime_input(blob)
            Gemini-->>Client: model_turn (audio/text)
            Client-->>Speaker: enqueue audio
        end
        Gemini-->>Client: server_closed_connection
        Client->>Client: cancel input_task, sleep, reconnect
    ```

 ## Runtime notes & tuning guidance
 - If responses cut off mid-speech, try these in order:
     1. Confirm `CHUNK` is `2048`. Larger chunks can raise latency and increase server timeouts; smaller chunks increase packet rate and CPU overhead.
     2. Increase `silence_duration_ms` in `CONFIG` to `1000`–`2000` ms to make the server wait longer for end-of-speech before starting a reply.
     3. Use headphones to eliminate feedback loops where the mic picks up the model's audio.
     4. Check network stability — intermittent connectivity can cause the server to close the connection.

 ## How to run
 1. Ensure your `.env` contains `GOOGLE_API_KEY`.
 2. Install Python deps (example):

 ```bash
 pip install pyaudio python-dotenv google-genai
 ```

 3. Run the agent:

 ```powershell
 python .\\voice_agent.py
 ```

 ## Troubleshooting hints
 - `Input Error` / `Output Error` prints include tracebacks — share them if you need help debugging.
 - If the model closes the connection immediately after connecting, check `CONFIG` for unsupported realtime fields (some models/API versions may reject unknown or unsupported keys).
 - If audio is choppy but connection remains, try a small `CHUNK` change: `1024` or `2048` are common sweet spots.

 ## Next steps you might want
 - Add an explicit VAD client-side signal (if supported) and toggle automatic detection.
 - Add logging of response timing (timestamps) to diagnose mid-response disconnects.
 - Add optional toggles in the prompt to force "Playful" or "Technical" modes on demand (e.g., voice commands like "be technical now").

 ---

 If you want, I can also:
 - Increase `silence_duration_ms` to 1–2s and test.
 - Add a runtime flag to switch personality modes manually.
 - Add a small test harness that sends prerecorded audio to the session for debugging.

