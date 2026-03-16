"""
data_preprocessing.py
Audio loading, format conversion, and normalization.
Supports WAV, MP3, and M4A formats.
"""

import os
import numpy as np
from pydub import AudioSegment
import librosa
from tqdm import tqdm

TARGET_SR = 16000
TARGET_CHANNELS = 1


def load_audio_file(filepath):
    """Load an audio file using pydub (handles WAV/MP3/M4A) and convert to numpy array."""
    ext = os.path.splitext(filepath)[1].lower()

    format_map = {
        '.wav': 'wav',
        '.mp3': 'mp3',
        '.m4a': 'm4a',
    }

    fmt = format_map.get(ext)
    if fmt is None:
        print(f"  [SKIP] Unsupported format: {filepath}")
        return None, None

    try:
        audio_seg = AudioSegment.from_file(filepath, format=fmt)

        # Convert to mono
        if audio_seg.channels > 1:
            audio_seg = audio_seg.set_channels(TARGET_CHANNELS)

        # Convert to target sample rate
        if audio_seg.frame_rate != TARGET_SR:
            audio_seg = audio_seg.set_frame_rate(TARGET_SR)

        # Convert to numpy float32
        samples = np.array(audio_seg.get_array_of_samples(), dtype=np.float32)

        # Normalize amplitude to [-1, 1]
        max_val = np.max(np.abs(samples))
        if max_val > 0:
            samples = samples / max_val

        return samples, TARGET_SR

    except Exception as e:
        print(f"  [ERROR] Failed to load {filepath}: {e}")
        return None, None


def load_dataset(data_dir):
    """
    Load all audio files from the dataset directory.

    Returns:
        list of dicts with keys:
            'audio': numpy array (float32, normalized)
            'sr': sample rate (16000)
            'category': 'fluent' or 'stutter'
            'filename': original filename
            'filepath': full path
    """
    dataset = []

    # Map folder names to categories
    folder_mapping = {}
    for folder_name in os.listdir(data_dir):
        folder_path = os.path.join(data_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue
        name_lower = folder_name.lower()
        if 'fluent' in name_lower:
            folder_mapping[folder_path] = 'fluent'
        elif 'stutter' in name_lower:
            folder_mapping[folder_path] = 'stutter'
        else:
            folder_mapping[folder_path] = folder_name

    print("=" * 60)
    print("STEP 1: Audio Preprocessing")
    print("=" * 60)

    for folder_path, category in folder_mapping.items():
        files = [f for f in os.listdir(folder_path)
                 if os.path.splitext(f)[1].lower() in ('.wav', '.mp3', '.m4a')]

        print(f"\nLoading {len(files)} files from '{os.path.basename(folder_path)}' ({category})...")

        for filename in tqdm(files, desc=f"  {category}"):
            filepath = os.path.join(folder_path, filename)
            audio, sr = load_audio_file(filepath)
            if audio is not None:
                duration = len(audio) / sr
                dataset.append({
                    'audio': audio,
                    'sr': sr,
                    'category': category,
                    'filename': filename,
                    'filepath': filepath,
                    'duration': duration,
                })

    total_duration = sum(d['duration'] for d in dataset)
    print(f"\nLoaded {len(dataset)} files | Total duration: {total_duration / 60:.1f} minutes")
    print(f"  Fluent: {sum(1 for d in dataset if d['category'] == 'fluent')} files")
    print(f"  Stutter: {sum(1 for d in dataset if d['category'] == 'stutter')} files")

    return dataset
