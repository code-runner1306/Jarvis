import os
import queue
import threading
import numpy as np
import sounddevice as sd
import openwakeword
from openwakeword.model import Model
import torch
import time

class VoiceListener:
    def __init__(self, wake_word="hey jarvis", callback=None, volume_callback=None):
        self.wake_word = wake_word
        self.callback = callback
        self.volume_callback = volume_callback
        self.audio_queue = queue.Queue()
        self.running = False
        
        # Load openWakeWord models
        self.oww_model = Model(wakeword_models=[wake_word])
        
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

    def _listen_loop(self):
        with sd.InputStream(samplerate=self.sample_rate, 
                            channels=1, 
                            callback=self._audio_callback,
                            blocksize=self.chunk_size):
            
            print(f"Listening for '{self.wake_word}'...")
            
            audio_buffer = []
            is_listening_to_speech = False
            
            while self.running:
                try:
                    chunk = self.audio_queue.get(timeout=1)
                except queue.Empty:
                    continue

                # Process for wake word
                self.oww_model.predict(chunk.flatten())
                
                # Check volume for UI
                if self.volume_callback:
                    volume = np.linalg.norm(chunk) / np.sqrt(len(chunk))
                    self.volume_callback(volume)

                # Get wake word confidence
                prediction = self.oww_model.prediction_probabilities[self.wake_word]
                
                if prediction > 0.5:
                    print("\nWake word detected!")
                    if self.callback:
                        self.callback("WAKE_WORD_DETECTED")
                    is_listening_to_speech = True
                    audio_buffer = [] # Start fresh for command
                    continue

                if is_listening_to_speech:
                    audio_buffer.append(chunk)
                    
                    # Check for silence using VAD after a certain amount of audio
                    if len(audio_buffer) > 5: # ~400ms
                        full_audio = np.concatenate(audio_buffer).flatten()
                        # Simple VAD check
                        speech_prob = self.vad_model(torch.from_numpy(full_audio[-self.chunk_size*4:]), self.sample_rate).item()
                        
                        if speech_prob < 0.3: # User stopped talking
                            print("Silence detected, processing...")
                            if self.callback:
                                self.callback("SPEECH_COMPLETE", full_audio)
                            is_listening_to_speech = False
                            audio_buffer = []
                
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
