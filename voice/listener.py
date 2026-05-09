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

# --- Listener States ---
STATE_WAKE_WORD = "WAKE_WORD"       # Passively listening for "Hey Jarvis"
STATE_WAITING   = "WAITING"         # Wake word heard, waiting for engine to say "start listening"
STATE_COMMAND   = "COMMAND"         # Actively capturing user's spoken command


class VoiceListener:
    def __init__(self, wake_word="hey_jarvis_v0.1", callback=None, volume_callback=None):
        self.wake_word = wake_word
        self.callback = callback
        self.volume_callback = volume_callback
        self.audio_queue = queue.Queue()
        self.running = False
        self.state = STATE_WAKE_WORD
        
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
        self.chunk_size = 1280  # 80ms chunks for openWakeWord
        
    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(status)
        self.audio_queue.put(indata.copy())

    def start(self):
        self.running = True
        self.state = STATE_WAKE_WORD
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=3)

    def enter_command_mode(self):
        """Called by the Engine after JARVIS finishes speaking his greeting."""
        print("[LISTENER] Entering COMMAND mode — speak your command now.")
        self.state = STATE_COMMAND

    def enter_wake_word_mode(self):
        """Called by the Engine after a command has been fully processed."""
        print(f"[LISTENER] Returning to WAKE_WORD mode — listening for '{self.wake_word}'...")
        self.state = STATE_WAKE_WORD

    def _listen_loop(self):
        with sd.InputStream(samplerate=self.sample_rate, 
                            channels=1, 
                            dtype='int16',
                            callback=self._audio_callback,
                            blocksize=self.chunk_size):
            
            print(f"[LISTENER] Online. Listening for '{self.wake_word}'...")
            
            audio_buffer = []
            has_started_speaking = False
            command_start_time = 0
            silence_chunks = 0  # Count consecutive silent chunks
            
            while self.running:
                try:
                    chunk = self.audio_queue.get(timeout=1)
                except queue.Empty:
                    continue

                # Always compute volume for UI callbacks
                if self.volume_callback:
                    volume_chunk = chunk.astype(np.float32) / 32768.0
                    volume = np.linalg.norm(volume_chunk) / np.sqrt(len(volume_chunk))
                    self.volume_callback(volume)

                # ─── STATE: WAKE_WORD ───
                if self.state == STATE_WAKE_WORD:
                    predictions = self.oww_model.predict(chunk.flatten())
                    prediction = predictions[self.wake_word]
                    
                    if prediction > 0.1:
                        print(f"  wake confidence: {prediction:.2f}", end="\r")
                    
                    if prediction > 0.5:
                        print(f"\n[DETECTED] Wake word detected! Confidence: {prediction:.2f}")
                        self.state = STATE_WAITING
                        if self.callback:
                            self.callback("WAKE_WORD_DETECTED")
                        # Drain the audio queue to discard wake word audio
                        while not self.audio_queue.empty():
                            try:
                                self.audio_queue.get_nowait()
                            except queue.Empty:
                                break

                # ─── STATE: WAITING ───
                elif self.state == STATE_WAITING:
                    # Do nothing with audio — just wait for the Engine to call
                    # enter_command_mode() after JARVIS finishes speaking.
                    pass

                # ─── STATE: COMMAND ───
                elif self.state == STATE_COMMAND:
                    audio_buffer.append(chunk)
                    
                    # Run VAD on each chunk (Silero expects exactly 512 samples at 16kHz)
                    current_chunk_f32 = chunk.flatten().astype(np.float32) / 32768.0
                    vad_input = torch.from_numpy(current_chunk_f32[:512])
                    speech_prob = self.vad_model(vad_input, self.sample_rate).item()
                    
                    if not has_started_speaking:
                        if speech_prob > 0.5:
                            has_started_speaking = True
                            command_start_time = time.time()
                            silence_chunks = 0
                            print("[LISTENER] User started speaking...")
                        else:
                            # Check for timeout (5 seconds of no speech)
                            if not command_start_time:
                                command_start_time = time.time()
                            if time.time() - command_start_time > 5.0:
                                print("[LISTENER] No speech detected in 5s, returning to wake word mode.")
                                audio_buffer = []
                                has_started_speaking = False
                                command_start_time = 0
                                silence_chunks = 0
                                self.state = STATE_WAKE_WORD
                    else:
                        # User is speaking — look for end-of-utterance silence
                        if speech_prob < 0.2:
                            silence_chunks += 1
                        else:
                            silence_chunks = 0
                        
                        # ~10 consecutive silent chunks ≈ 800ms of silence → end of command
                        if silence_chunks >= 10:
                            full_audio = np.concatenate(audio_buffer).flatten()
                            # Only process if we have meaningful audio (> 0.5s)
                            if len(full_audio) > self.sample_rate * 0.5:
                                print("[LISTENER] End of speech detected, processing command...")
                                self.state = STATE_WAITING  # Pause while engine processes
                                if self.callback:
                                    self.callback("SPEECH_COMPLETE", full_audio)
                            else:
                                print("[LISTENER] Audio too short, ignoring.")
                                self.state = STATE_WAKE_WORD
                            
                            # Reset for next command
                            audio_buffer = []
                            has_started_speaking = False
                            command_start_time = 0
                            silence_chunks = 0
                            # Short sleep to avoid tail-end re-triggers
                            time.sleep(0.3)


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
