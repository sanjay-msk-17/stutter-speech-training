"""
feature_cache_manager.py
Incremental feature caching system with pause/resume support.
Features are saved per-segment as .pkl files via joblib.
On restart, already-processed segments are automatically skipped.
"""

import os
import joblib
import numpy as np
from tqdm import tqdm
from feature_extraction import extract_features

CACHE_DIR = "feature_cache"


def ensure_cache_dir():
    """Create the feature cache directory if it doesn't exist."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def get_cached_segment_ids():
    """
    Scan the cache directory and return a set of already-processed segment IDs.
    """
    ensure_cache_dir()
    cached_ids = set()
    for fname in os.listdir(CACHE_DIR):
        if fname.endswith('.pkl'):
            seg_id = fname.replace('.pkl', '')
            cached_ids.add(seg_id)
    return cached_ids


def save_segment_cache(segment_id, feature_vector, metadata):
    """Save a single segment's features and metadata to cache."""
    ensure_cache_dir()
    cache_data = {
        'feature_vector': feature_vector,
        'metadata': metadata,
    }
    filepath = os.path.join(CACHE_DIR, f"{segment_id}.pkl")
    joblib.dump(cache_data, filepath)


def extract_and_cache_features(segments_list):
    """
    Extract features from segments with caching support.
    Skips already-cached segments. Saves each segment immediately after extraction.

    This allows safe interruption (Ctrl+C) — on restart, processing
    resumes from where it left off.

    Args:
        segments_list: list of segment dicts from segmentation.process_dataset_segments()

    Returns:
        tuple: (feature_matrix, metadata_list)
    """
    print("\n" + "=" * 60)
    print("STEP 4 & 5: Feature Extraction with Caching")
    print("=" * 60)

    cached_ids = get_cached_segment_ids()
    total = len(segments_list)
    already_cached = sum(1 for s in segments_list if s['segment_id'] in cached_ids)

    if already_cached > 0:
        print(f"\n  Found {already_cached}/{total} segments already cached. Resuming...")
    else:
        print(f"\n  Processing {total} segments from scratch...")

    # Extract features for uncached segments
    newly_processed = 0
    for seg_info in tqdm(segments_list, desc="  Extracting features"):
        seg_id = seg_info['segment_id']

        if seg_id in cached_ids:
            continue  # Skip already processed

        # Extract features
        feature_vector = extract_features(seg_info['segment'], seg_info['sr'])

        # Build metadata
        metadata = {
            'segment_id': seg_id,
            'category': seg_info['category'],
            'source_file': seg_info['source_file'],
            'segment_idx': seg_info['segment_idx'],
        }

        # Save immediately (crash-safe)
        save_segment_cache(seg_id, feature_vector, metadata)
        newly_processed += 1

    print(f"\n  Newly processed: {newly_processed} segments")
    print(f"  Total cached: {already_cached + newly_processed} segments")

    # Load all cached features
    return load_all_cached_features()


def load_all_cached_features():
    """
    Load all cached feature vectors and metadata from the cache directory.

    Returns:
        tuple: (feature_matrix: np.ndarray of shape (N, 47),
                metadata_list: list of metadata dicts)
    """
    ensure_cache_dir()
    cache_files = sorted([f for f in os.listdir(CACHE_DIR) if f.endswith('.pkl')])

    if len(cache_files) == 0:
        print("  [WARNING] No cached features found!")
        return np.array([]), []

    features = []
    metadata_list = []

    for fname in cache_files:
        filepath = os.path.join(CACHE_DIR, fname)
        data = joblib.load(filepath)
        features.append(data['feature_vector'])
        metadata_list.append(data['metadata'])

    feature_matrix = np.array(features, dtype=np.float32)

    print(f"\n  Loaded {len(features)} feature vectors | Shape: {feature_matrix.shape}")

    return feature_matrix, metadata_list
