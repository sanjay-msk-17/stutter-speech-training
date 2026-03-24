"""
feature_extraction.py
Extract acoustic features from audio segments:
MFCC (13), Delta MFCC (13), Delta-Delta MFCC (13),
Pitch (2), Energy (2), ZCR (2), Spectral Centroid (2),
Spectral Bandwidth (2), Spectral Flatness (2), Spectral Rolloff (2)
Total: 53-dimensional feature vector per segment.
"""

import numpy as np
import librosa
import warnings
warnings.filterwarnings('ignore')

N_MFCC = 13


def extract_features(audio_segment, sr=16000):
    """
    Extract a 47-dimensional feature vector from an audio segment.

    Features:
        - MFCC (13 coefficients, mean across frames)
        - Delta MFCC (13, mean across frames)
        - Delta-Delta MFCC (13, mean across frames)
        - Pitch: mean and std of fundamental frequency
        - Energy: mean and std of RMS energy
        - Zero Crossing Rate: mean and std
        - Spectral Centroid: mean and std

    Args:
        audio_segment: numpy array of audio samples
        sr: sample rate

    Returns:
        numpy array of shape (47,)
    """
    # Ensure float32
    audio_segment = audio_segment.astype(np.float32)

    # Handle empty or near-silent segments
    if len(audio_segment) < sr * 0.1 or np.max(np.abs(audio_segment)) < 1e-6:
        return np.zeros(53, dtype=np.float32)

    # --- MFCC (13 coefficients) ---
    mfcc = librosa.feature.mfcc(y=audio_segment, sr=sr, n_mfcc=N_MFCC)
    mfcc_mean = np.mean(mfcc, axis=1)  # (13,)

    # --- Delta MFCC ---
    delta_mfcc = librosa.feature.delta(mfcc)
    delta_mfcc_mean = np.mean(delta_mfcc, axis=1)  # (13,)

    # --- Delta-Delta MFCC ---
    delta2_mfcc = librosa.feature.delta(mfcc, order=2)
    delta2_mfcc_mean = np.mean(delta2_mfcc, axis=1)  # (13,)

    # --- Pitch (F0) ---
    try:
        f0, voiced_flag, voiced_probs = librosa.pyin(
            audio_segment, fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'), sr=sr
        )
        f0_clean = f0[~np.isnan(f0)]
        if len(f0_clean) > 0:
            pitch_mean = np.mean(f0_clean)
            pitch_std = np.std(f0_clean)
        else:
            pitch_mean, pitch_std = 0.0, 0.0
    except Exception:
        pitch_mean, pitch_std = 0.0, 0.0

    # --- Energy (RMS) ---
    rms = librosa.feature.rms(y=audio_segment)[0]
    energy_mean = np.mean(rms)
    energy_std = np.std(rms)

    # --- Zero Crossing Rate ---
    zcr = librosa.feature.zero_crossing_rate(audio_segment)[0]
    zcr_mean = np.mean(zcr)
    zcr_std = np.std(zcr)

    # --- Spectral Centroid ---
    spec_centroid = librosa.feature.spectral_centroid(y=audio_segment, sr=sr)[0]
    sc_mean = np.mean(spec_centroid)
    sc_std = np.std(spec_centroid)

    # --- Spectral Bandwidth ---
    spec_bw = librosa.feature.spectral_bandwidth(y=audio_segment, sr=sr)[0]
    bw_mean = np.mean(spec_bw)
    bw_std = np.std(spec_bw)

    # --- Spectral Flatness ---
    spec_flat = librosa.feature.spectral_flatness(y=audio_segment)[0]
    flat_mean = np.mean(spec_flat)
    flat_std = np.std(spec_flat)

    # --- Spectral Rolloff ---
    spec_rolloff = librosa.feature.spectral_rolloff(y=audio_segment, sr=sr)[0]
    rolloff_mean = np.mean(spec_rolloff)
    rolloff_std = np.std(spec_rolloff)

    # Combine all features into single vector
    feature_vector = np.concatenate([
        mfcc_mean,           # 13
        delta_mfcc_mean,     # 13
        delta2_mfcc_mean,    # 13
        [pitch_mean, pitch_std],          # 2
        [energy_mean, energy_std],        # 2
        [zcr_mean, zcr_std],              # 2
        [sc_mean, sc_std],                # 2
        [bw_mean, bw_std],                # 2
        [flat_mean, flat_std],            # 2
        [rolloff_mean, rolloff_std],      # 2
    ]).astype(np.float32)  # Total: 53

    return feature_vector


def extract_features_batch(segments_list):
    """
    Extract features from a list of segment dicts.
    Returns list of (feature_vector, metadata) tuples.
    """
    results = []
    for seg_info in segments_list:
        feat = extract_features(seg_info['segment'], seg_info['sr'])
        results.append((feat, {
            'segment_id': seg_info['segment_id'],
            'category': seg_info['category'],
            'source_file': seg_info['source_file'],
            'segment_idx': seg_info['segment_idx'],
        }))
    return results
