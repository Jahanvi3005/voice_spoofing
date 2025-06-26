import numpy as np
from scipy.io.wavfile import write as write_wav

def generate_fake_wav(filename="fake_audio.wav", duration_seconds=5, sample_rate=44100, is_silent=True):
    """
    Generates a simple .wav audio file.

    Args:
        filename (str): The name of the output .wav file.
        duration_seconds (int): The duration of the audio in seconds.
        sample_rate (int): The sample rate of the audio (samples per second).
        is_silent (bool): If True, generates a silent audio file.
                          If False, generates a simple sine wave.
    """
    num_samples = int(duration_seconds * sample_rate)

    if is_silent:
        # Generate silent audio (all zeros)
        audio_data = np.zeros(num_samples, dtype=np.int16)
        print(f"Generating a {duration_seconds}-second silent audio file: {filename}")
    else:
        # Generate a sine wave (e.g., 440 Hz A4 note)
        frequency = 440  # Hz
        amplitude = 0.5   # 0.0 to 1.0
        
        # Create a time array
        t = np.linspace(0, duration_seconds, num_samples, endpoint=False)
        
        # Generate sine wave and scale to 16-bit integer range
        # int16 range is -32768 to 32767
        audio_data = (amplitude * np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)
        print(f"Generating a {duration_seconds}-second sine wave audio file ({frequency} Hz): {filename}")

    # Write the audio data to a WAV file
    write_wav(filename, sample_rate, audio_data)
    print(f"File '{filename}' created successfully in the current directory.")

if __name__ == "__main__":
    # Example 1: Generate a 5-second silent WAV file
    generate_fake_wav("silent_fake_audio.wav", duration_seconds=5, is_silent=True)

    # Example 2: Generate a 3-second WAV file with a sine wave
    generate_fake_wav("sine_wave_fake_audio.wav", duration_seconds=3, is_silent=False)
