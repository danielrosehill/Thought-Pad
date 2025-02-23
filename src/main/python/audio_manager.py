import sounddevice as sd
import numpy as np
from pathlib import Path
import tempfile
import wave
import threading
import queue
import time

class AudioManager:
    def __init__(self):
        self.recording = False
        self.paused = False
        self.audio_queue = queue.Queue()
        self.recorded_frames = []
        self.frames_lock = threading.Lock()
        self.sample_rate = 44100
        self.channels = 1
        self.temp_file = None
        self.recording_thread = None
        self._create_temp_file()

    def _create_temp_file(self):
        """Create a temporary WAV file for recording."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)

    def get_available_devices(self):
        """Get list of available audio input devices."""
        devices = sd.query_devices()
        input_devices = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels']
                })
        return input_devices

    def set_device(self, device_index):
        """Set the audio input device."""
        try:
            sd.default.device[0] = device_index
            return True
        except Exception as e:
            print(f"Error setting audio device: {e}")
            return False

    def _audio_callback(self, indata, frames, time, status):
        """Callback function for audio recording."""
        if status:
            print(status)
        if not self.paused:
            self.audio_queue.put(indata.copy())
            with self.frames_lock:
                self.recorded_frames.append(indata.copy())

    def start_recording(self):
        """Start audio recording."""
        if not self.recording:
            self.recording = True
            self.paused = False
            self.recorded_frames = []
            self.recording_thread = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback
            )
            self.recording_thread.start()

    def pause_recording(self):
        """Pause audio recording."""
        self.paused = True

    def resume_recording(self):
        """Resume audio recording."""
        self.paused = False

    def stop_recording(self):
        """Stop audio recording and save to temporary file."""
        if self.recording:
            self.recording = False
            self.paused = False
            if self.recording_thread:
                self.recording_thread.stop()
                self.recording_thread.close()
            self._save_recording()

    def _save_recording(self):
        """Save recorded audio to WAV file."""
        if not self.recorded_frames:
            return None

        try:
            with wave.open(self.temp_file.name, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(self.sample_rate)
                for frame in self.recorded_frames:
                    wf.writeframes((frame * 32767).astype(np.int16).tobytes())
            return self.temp_file.name
        except Exception as e:
            print(f"Error saving recording: {e}")
            return None

    def get_temp_file_path(self):
        """Get the path to the temporary recording file."""
        return self.temp_file.name if self.temp_file else None

    def clear_recording(self):
        """Clear the current recording."""
        self.recorded_frames = []
        if self.temp_file:
            try:
                Path(self.temp_file.name).unlink(missing_ok=True)
                self._create_temp_file()
            except Exception as e:
                print(f"Error clearing recording: {e}")

    def get_waveform_data(self):
        """Get waveform data for visualization."""
        with self.frames_lock:
            if not self.recorded_frames:
                return np.array([])
            return np.concatenate(self.recorded_frames.copy())

    def __del__(self):
        """Cleanup temporary files."""
        if self.temp_file:
            try:
                Path(self.temp_file.name).unlink(missing_ok=True)
            except Exception:
                pass