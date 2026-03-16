"""
pseudo_labeling.py
Generate pseudo labels from HMM hidden states.
Maps discovered temporal patterns to stutter class labels using
source category info and acoustic feature characteristics.
"""

import numpy as np
from collections import Counter

# Target stutter classes
STUTTER_CLASSES = [
    'Fluent Speech',
    'Block',
    'Prolongation',
    'Sound Repetition',
    'Word Repetition',
    'Interjection',
]

# Feature indices for heuristic mapping
# MFCC: 0-12, Delta: 13-25, Delta2: 26-38
# Pitch: 39-40, Energy: 41-42, ZCR: 43-44, Spectral Centroid: 45-46
# Spectral Bandwidth: 47-48, Spectral Flatness: 49-50, Spectral Rolloff: 51-52
IDX_PITCH_MEAN = 39
IDX_PITCH_STD = 40
IDX_ENERGY_MEAN = 41
IDX_ENERGY_STD = 42
IDX_ZCR_MEAN = 43
IDX_ZCR_STD = 44
IDX_SC_MEAN = 45
IDX_SC_STD = 46
IDX_BW_MEAN = 47
IDX_BW_STD = 48
IDX_FLAT_MEAN = 49
IDX_FLAT_STD = 50
IDX_ROLLOFF_MEAN = 51
IDX_ROLLOFF_STD = 52

# Delta-MFCC indices (for Word Repetition detection)
IDX_DELTA_MFCC_START = 13
IDX_DELTA_MFCC_END = 26


def generate_pseudo_labels(hmm_model, feature_matrix, metadata_list):
    """
    Generate pseudo labels using ground-truth categories + HMM sub-typing.

    Strategy:
    1. Segments from 'fluent' source folder -> always 'Fluent Speech'
    2. Segments from 'stutter' source folder -> use HMM states + acoustic
       heuristics to assign a specific stutter sub-type
    
    This ensures the fluent/stutter boundary uses real ground truth,
    while the HMM is only used for stutter sub-type classification.

    Args:
        hmm_model: trained HMM model
        feature_matrix: numpy array (N, 47)
        metadata_list: list of metadata dicts with 'category' key

    Returns:
        tuple: (pseudo_labels: list of str, state_sequence: numpy array)
    """
    print("\n" + "=" * 60)
    print("STEP 7: Pseudo Label Generation")
    print("=" * 60)

    # Clean feature matrix
    feature_matrix_clean = np.nan_to_num(feature_matrix, nan=0.0, posinf=0.0, neginf=0.0)

    # Predict hidden states for all segments
    state_sequence = hmm_model.predict(feature_matrix_clean)
    n_states = hmm_model.n_components

    print(f"\n  HMM states: {Counter(state_sequence)}")

    # ---- Step A: Identify fluent vs stutter segments from metadata ----
    fluent_indices = [i for i, m in enumerate(metadata_list) if m['category'] == 'fluent']
    stutter_indices = [i for i, m in enumerate(metadata_list) if m['category'] != 'fluent']

    print(f"  Fluent segments (from folder): {len(fluent_indices)}")
    print(f"  Stutter segments (from folder): {len(stutter_indices)}")

    # ---- Step B: For stutter segments, classify each individually ----
    # Instead of mapping HMM states to classes (which causes uneven distribution
    # when some states have very few segments), we classify each stutter segment
    # individually based on its acoustic features.

    print(f"  Classifying each stutter segment by acoustic features...")

    # Classify all stutter segments at once (uses z-score normalization)
    stutter_classifications = _classify_stutter_segments(feature_matrix_clean, stutter_indices)

    # ---- Step C: Assign labels ----
    pseudo_labels = []
    for i, meta in enumerate(metadata_list):
        if meta['category'] == 'fluent':
            pseudo_labels.append('Fluent Speech')
        else:
            pseudo_labels.append(stutter_classifications.get(i, 'Interjection'))

    # Print distribution
    label_counts = Counter(pseudo_labels)
    print(f"\n  Pseudo label distribution:")
    for cls in STUTTER_CLASSES:
        count = label_counts.get(cls, 0)
        pct = count / len(pseudo_labels) * 100
        print(f"    {cls:20s}: {count:5d} ({pct:5.1f}%)")

    return pseudo_labels, state_sequence


def _classify_stutter_segments(feature_matrix, stutter_indices):
    """
    Classify stutter segments into sub-types using normalized acoustic scoring.

    Each segment is scored against all 5 stutter class criteria using
    z-score normalized features for fair comparison across metrics.

    Args:
        feature_matrix: full feature matrix (N, 53)
        stutter_indices: list of indices into feature_matrix that are stutter segments

    Returns:
        dict mapping index -> class label
    """
    if len(stutter_indices) == 0:
        return {}

    stutter_feats = feature_matrix[stutter_indices]

    # Extract relevant features for all stutter segments
    energy_mean = stutter_feats[:, IDX_ENERGY_MEAN]
    energy_std = stutter_feats[:, IDX_ENERGY_STD]
    pitch_std = stutter_feats[:, IDX_PITCH_STD]
    zcr_std = stutter_feats[:, IDX_ZCR_STD]
    bw_std = stutter_feats[:, IDX_BW_STD]
    flat_std = stutter_feats[:, IDX_FLAT_STD]
    rolloff_std = stutter_feats[:, IDX_ROLLOFF_STD]
    delta_mfcc_var = np.mean(np.abs(stutter_feats[:, IDX_DELTA_MFCC_START:IDX_DELTA_MFCC_END]), axis=1)

    def z_normalize(arr):
        """Z-score normalize, handling zero std."""
        std = np.std(arr)
        if std < 1e-10:
            return np.zeros_like(arr)
        return (arr - np.mean(arr)) / std

    # Z-normalize all features so scores are comparable
    energy_mean_z = z_normalize(energy_mean)
    energy_std_z = z_normalize(energy_std)
    pitch_std_z = z_normalize(pitch_std)
    zcr_std_z = z_normalize(zcr_std)
    bw_std_z = z_normalize(bw_std)
    flat_std_z = z_normalize(flat_std)
    rolloff_std_z = z_normalize(rolloff_std)
    delta_mfcc_z = z_normalize(delta_mfcc_var)

    n = len(stutter_indices)

    # Compute score for each class (higher = more likely)
    # Using negative z-scores for "low X" criteria and positive for "high X"
    scores = np.zeros((n, 5))  # 5 stutter classes

    # Block: low energy mean + low energy variance
    scores[:, 0] = -energy_mean_z - energy_std_z

    # Prolongation: low pitch variance + high energy (sustained sound)
    scores[:, 1] = -pitch_std_z + energy_mean_z

    # Sound Repetition: high ZCR variance + high energy variance
    scores[:, 2] = zcr_std_z + energy_std_z

    # Word Repetition: high delta-MFCC + high rolloff variance
    scores[:, 3] = delta_mfcc_z + rolloff_std_z

    # Interjection: low bandwidth variance + low spectral flatness variance
    scores[:, 4] = -bw_std_z - flat_std_z

    class_names = ['Block', 'Prolongation', 'Sound Repetition', 'Word Repetition', 'Interjection']

    # Assign each segment to the highest scoring class
    assignments = np.argmax(scores, axis=1)

    result = {}
    for idx, stutter_idx in enumerate(stutter_indices):
        result[stutter_idx] = class_names[assignments[idx]]

    return result

