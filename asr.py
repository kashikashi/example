import whisper
import sounddevice as sd
import numpy as np
import threading
import queue
import soundfile as sf
import re
import sys

# Configure system input and output encodings to UTF-8
sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

# Global variables
recording = False
audio_queue = queue.Queue()
samplerate = 16000  # Sampling rate
whisper_model_type = "tiny"  # Model type (tiny/base/small/medium/large-v2)

# Audio recording function
def record_audio(q):
    global recording
    with sd.InputStream(samplerate=samplerate, channels=1, callback=lambda indata, frames, time, status: q.put(indata.copy())):
        while recording:
            sd.sleep(1000)

# Function to wait for recording start command
def wait_for_start():
    while True:
        user_input = input("To start recording, type 'START'...\n", file=sys.stderr)
        if user_input.lower() == "start":
            return

# Function to wait for recording stop command
def wait_for_end():
    while True:
        user_input = input("To stop recording, type 'END'...\n", file=sys.stderr)
        if user_input.lower() == "end":
            return

# Function to wait for a tap event
def wait_for_tap():
    while True:
        instr = input().strip()
        if not instr:
            break
        # Check if the input is a RECOG_EVENT_STOP
        utterance = re.findall('^TAPPED\|(.*)$', instr)
        if utterance:
            return

# Speech recognition function
def recognize_speech(audio, model):
    print("Starting speech recognition...", file=sys.stderr)
    result = model.transcribe(audio, language='ja')
    print("Speech recognition completed", file=sys.stderr)
    return result['text']

# Function to save audio data to a file
def save_audio_to_file(audio, filename, samplerate):
    sf.write(filename, audio, samplerate)

# Main function
def main():
    global recording

    # Load the Whisper model
    model = whisper.load_model(whisper_model_type)
    print("Model loaded.", file=sys.stderr)

    while True:
        # Wait for the recording to start
        wait_for_tap()
        print("Starting recording...", file=sys.stderr)
        print("RECOG_EVENT_START")

        recording = True

        # Start recording thread
        audio_thread = threading.Thread(target=record_audio, args=(audio_queue,))
        audio_thread.start()

        # Wait for the recording to stop
        wait_for_tap()
        print("Stopping recording...", file=sys.stderr)

        # Stop recording
        recording = False
        audio_thread.join()

        # Retrieve recorded audio
        recorded_audio = np.concatenate(list(audio_queue.queue)).flatten()

        # Perform speech recognition
        text = recognize_speech(recorded_audio, model)
        print("Recognized text: " + text, file=sys.stderr)
        print("RECOG_EVENT_STOP|" + text)

        # Clear the audio queue
        with audio_queue.mutex:
            audio_queue.queue.clear()

# Execute
if __name__ == "__main__":
    main()
