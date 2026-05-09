import os
import queue
import threading
import numpy as np
import sounddevice as sd
import openwakeword
from openwakeword.model import Model
import torch
import time
import warnings

# Suppress annoying warnings
warnings.filterwarnings("ignore", category=UserWarning)
try:
    from langchain_core._api.deprecation import LangChainPendingDeprecationWarning
    warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
except ImportError:
    pass

class VoiceListener:
    def __init__(self, wake_word="hey_jarvis_v0.1", callback=None, volume_callback=None):
        self.wake_word = wake_word
        self.callback = callback
        self.volume_callback = volume_callback
        self.audio_queue = queue.Queue()
        self.running = False
        self.command_start_time = 0
        
        # Load specific openWakeWord model path
        model_paths = openwakeword.get_pretrained_model_paths()
        jarvis_path = [p for p in model_paths if "hey_jarvis" in p]
        
        if not jarvis_path:
            raise FileNotFoundError("Could not find pretrained 'hey_jarvis' model.")
            
        self.oww_model = Model(wakeword_model_paths=[jarvis_path[0]])
        
        # Load Silero VAD
        self.vad_model, self.vad_utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                                        model='silero_vad',
                                                        force_reload=False)
        (self.get_speech_timestamps, _, self.read_audio, _, _) = self.vad_utils

        self.sample_rate = 16000
        self.chunk_size = 1280 # 80ms chunks for openWakeWord
        
    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.audio_queue.put(indata.copy())

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def reset_timeout(self):
        self.command_start_time = time.time()

    def _listen_loop(self):
        with sd.InputStream(samplerate=self.sample_rate, 
                            channels=1, 
                            dtype='int16',
                            callback=self._audio_callback,
                            blocksize=self.chunk_size):
            
            print(f"Listening for '{self.wake_word}'...")
            
            audio_buffer = []
            is_listening_to_speech = False
            has_started_speaking = False
            self.command_start_time = 0
            
            while self.running:
                try:
                    chunk = self.audio_queue.get(timeout=1)
                except queue.Empty:
                    continue

                # Process for wake word
                predictions = self.oww_model.predict(chunk.flatten())
                
                # Check volume for UI
                if self.volume_callback:
                    volume_chunk = chunk.astype(np.float32) / 32768.0
                    volume = np.linalg.norm(volume_chunk) / np.sqrt(len(volume_chunk))
                    self.volume_callback(volume)

                # Get wake word confidence
                prediction = predictions[self.wake_word]
                
                # Debug: Print confidence if it's non-trivial
                if not is_listening_to_speech and prediction > 0.1:
                    print(f"Wake word confidence: {prediction:.2f}", end="\r")
                
                if not is_listening_to_speech and prediction > 0.5:
                    print(f"\n[DETECTED] Wake word detected! Confidence: {prediction:.2f}")
                    if self.callback:
                        self.callback("WAKE_WORD_DETECTED")
                    is_listening_to_speech = True
                    has_started_speaking = False
                    self.command_start_time = time.time()
                    audio_buffer = []
                    continue

                if is_listening_to_speech:
                    audio_buffer.append(chunk)
                    
                    # Check VAD
                    current_chunk = chunk.flatten().astype(np.float32) / 32768.0
                    vad_input = torch.from_numpy(current_chunk[-512:])
                    speech_prob = self.vad_model(vad_input, self.sample_rate).item()
                    
                    # If we haven't started speaking, look for high speech probability
                    if not has_started_speaking:
                        if speech_prob > 0.6:
                            has_started_speaking = True
                            print("[LISTENER] User started speaking...")
                        
                        # Timeout if no speech after 3 seconds
                        if time.time() - self.command_start_time > 3.0:
                            print("[LISTENER] Command timeout (no speech detected).")
                            is_listening_to_speech = False
                            audio_buffer = []
                    
                    # If we ARE speaking, look for silence to end the command
                    else:
                        # We need a bit of buffer to confirm silence (e.g., 800ms of low prob)
                        # For simplicity, we'll check if the last few chunks are silent
                        if speech_prob < 0.2:
                            # Verify with a bit more audio
                            full_audio = np.concatenate(audio_buffer).flatten()
                            # If we have at least 1 second of audio and it's quiet
                            if len(full_audio) > self.sample_rate * 1.0:
                                print("[LISTENER] Silence detected, processing command...")
                                if self.callback:
                                    self.callback("SPEECH_COMPLETE", full_audio)
                                is_listening_to_speech = False
                                audio_buffer = []
                                has_started_speaking = False
                                # Short sleep to avoid immediate re-trigger from tail of speech
                                time.sleep(0.5)
                
if __name__ == "__main__":
    def test_callback(event, data=None):
        print(f"Event: {event}")
        
    listener = VoiceListener(callback=test_callback)
    listener.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
