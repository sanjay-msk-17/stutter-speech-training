"""
segmentation.py
Voice Activity Detection (silence removal) and audio segmentation
into overlapping windows for stuttering pattern capture.
"""

import numpy as np
import librosa
from tqdm import tqdm

# Segmentation parameters
SEGMENT_DURATION = 3.0    # seconds
OVERLAP = 0.5             # 50% overlap
HOP_DURATION = SEGMENT_DURATION * (1 - OVERLAP)  # 1.5 seconds

# VAD parameters
VAD_TOP_DB = 25           # dB threshold for silence detection


def remove_silence(audio, sr, top_db=VAD_TOP_DB):
    """
    Apply Voice Activity Detection to remove silence regions.

    Uses librosa.effects.split() to detect non-silent intervals
    and concatenates only speech portions.
    """
    # Detect non-silent intervals
    intervals = librosa.effects.split(audio, top_db=top_db)

    if len(intervals) == 0:
        return audio  # Return original if no speech detected

    # Concatenate speech regions
    speech_parts = []
    for start, end in intervals:
        speech_parts.append(audio[start:end])

    speech_audio = np.concatenate(speech_parts)
    return speech_audio


def segment_audio(audio, sr, segment_duration=SEGMENT_DURATION, overlap=OVERLAP):
    """
    Segment audio into overlapping windows.

    Args:
        audio: numpy array of audio samples
        sr: sample rate
        segment_duration: length of each segment in seconds
        overlap: overlap fraction (0.5 = 50%)

    Returns:
        list of numpy arrays, each a segment
    """
    segment_samples = int(segment_duration * sr)
    hop_samples = int(segment_samples * (1 - overlap))

    segments = []
    start = 0

    while start + segment_samples <= len(audio):
        segment = audio[start:start + segment_samples]
        segments.append(segment)
        start += hop_samples

    # Handle last partial segment (pad with zeros if needed)
    if start < len(audio) and len(audio) - start > segment_samples * 0.3:
        last_segment = audio[start:]
        # Pad to full segment length
        padded = np.zeros(segment_samples, dtype=np.float32)
        padded[:len(last_segment)] = last_segment
        segments.append(padded)

    return segments


def process_dataset_segments(dataset):
    """
    Apply silence removal and segmentation to entire dataset.

    Args:
        dataset: list of dicts from data_preprocessing.load_dataset()

    Returns:
        list of dicts with keys:
            'segment': numpy array (audio segment)
            'sr': sample rate
            'category': 'fluent' or 'stutter'
            'source_file': original filename
            'segment_idx': index within the source file
            'segment_id': globally unique segment identifier
    """
    print("\n" + "=" * 60)
    print("STEP 2 & 3: Silence Removal + Segmentation")
    print("=" * 60)

    all_segments = []
    global_idx = 0

    for item in tqdm(dataset, desc="  Processing files"):
        audio = item['audio']
        sr = item['sr']

        # Step 2: Remove silence
        speech_audio = remove_silence(audio, sr)

        # Step 3: Segment into overlapping windows
        segments = segment_audio(speech_audio, sr)

        for seg_idx, segment in enumerate(segments):
            all_segments.append({
                'segment': segment,
                'sr': sr,
                'category': item['category'],
                'source_file': item['filename'],
                'segment_idx': seg_idx,
                'segment_id': f"segment_{global_idx:05d}",
            })
            global_idx += 1

    # Print summary
    fluent_count = sum(1 for s in all_segments if s['category'] == 'fluent')
    stutter_count = sum(1 for s in all_segments if s['category'] == 'stutter')
    print(f"\nGenerated {len(all_segments)} segments total")
    print(f"  Fluent segments:  {fluent_count}")
    print(f"  Stutter segments: {stutter_count}")
    print(f"  Segment duration: {SEGMENT_DURATION}s | Overlap: {OVERLAP * 100:.0f}%")

    return all_segments
