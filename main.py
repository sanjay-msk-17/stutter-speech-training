"""
main.py
Pipeline orchestrator for the Semi-Supervised Stuttering Detection System.

Runs the full pipeline:
  1. Audio Preprocessing
  2. Silence Removal
  3. Audio Segmentation
  4. Feature Extraction (with caching / pause-resume)
  5. HMM-GMM Temporal Modeling
  6. Pseudo Label Generation
  7. SVM Classifier Training
  8. Model Evaluation
  9. Visualization

Usage:
    python main.py

Feature extraction can be paused (Ctrl+C) and resumed safely.
"""

import os
import sys
import time
import numpy as np

# Project modules
from data_preprocessing import load_dataset
from segmentation import process_dataset_segments
from feature_cache_manager import extract_and_cache_features, load_all_cached_features
from hmm_training import train_hmm
from pseudo_labeling import generate_pseudo_labels
from svm_classifier import train_svm
from visualization import generate_all_visualizations

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def print_header():
    print("\n" + "=" * 60)
    print("  Semi-Supervised Stuttering Detection System")
    print("  HMM-GMM + SVM Pipeline")
    print("=" * 60)
    print(f"  Data directory: {DATA_DIR}")
    print(f"  Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def main():
    print_header()
    start_time = time.time()

    # --------------------------------------------------------
    # Step 1: Audio Preprocessing
    # --------------------------------------------------------
    dataset = load_dataset(DATA_DIR)
    if len(dataset) == 0:
        print("\n[ERROR] No audio files found in the dataset!")
        sys.exit(1)

    # --------------------------------------------------------
    # Steps 2 & 3: Silence Removal + Segmentation
    # --------------------------------------------------------
    segments = process_dataset_segments(dataset)
    if len(segments) == 0:
        print("\n[ERROR] No segments generated!")
        sys.exit(1)

    # Free memory — audio data no longer needed
    del dataset

    # --------------------------------------------------------
    # Steps 4 & 5: Feature Extraction with Caching
    # (Can be paused with Ctrl+C and resumed on next run)
    # --------------------------------------------------------
    try:
        feature_matrix, metadata_list = extract_and_cache_features(segments)
    except KeyboardInterrupt:
        print("\n\n  [PAUSED] Feature extraction paused by user.")
        print("  Run this script again to resume from where you left off.")
        print(f"  Progress saved in: feature_cache/")
        sys.exit(0)

    # Free memory — raw segments no longer needed
    del segments

    if len(feature_matrix) == 0:
        print("\n[ERROR] No features extracted!")
        sys.exit(1)

    # --------------------------------------------------------
    # Step 6: HMM-GMM Temporal Modeling
    # --------------------------------------------------------
    hmm_model = train_hmm(feature_matrix)

    # --------------------------------------------------------
    # Step 7: Pseudo Label Generation
    # --------------------------------------------------------
    pseudo_labels, state_sequence = generate_pseudo_labels(
        hmm_model, feature_matrix, metadata_list
    )

    # --------------------------------------------------------
    # Step 8 & 9: SVM Classifier Training + Evaluation
    # --------------------------------------------------------
    svm_model, scaler, label_encoder, results = train_svm(
        feature_matrix, pseudo_labels
    )

    # --------------------------------------------------------
    # Step 10: Visualizations
    # --------------------------------------------------------
    generate_all_visualizations(
        feature_matrix, pseudo_labels, metadata_list, results
    )

    # --------------------------------------------------------
    # Step 11: Final Output Summary
    # --------------------------------------------------------
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("  FINAL RESULTS")
    print("=" * 60)
    print(f"\n  Overall Accuracy:  {results['accuracy']:.4f}")
    print(f"  Precision:         {results['precision']:.4f}")
    print(f"  Recall:            {results['recall']:.4f}")
    print(f"  F1 Score:          {results['f1']:.4f}")
    print(f"  CV Accuracy:       {results['cv_accuracy']:.4f} (+/- {results['cv_std'] * 2:.4f})")

    print(f"\n  Classification Report:")
    print(results['classification_report'])

    # Print per-segment predictions summary
    print(f"\n  Predicted class for each segment (first 20):")
    print(f"  {'Segment ID':<20s} {'Source File':<45s} {'Predicted Class'}")
    print(f"  {'-'*20} {'-'*45} {'-'*20}")
    for i, (label, meta) in enumerate(zip(pseudo_labels, metadata_list)):
        if i >= 20:
            print(f"  ... and {len(pseudo_labels) - 20} more segments")
            break
        fname = meta['source_file'][:42]
        print(f"  {meta['segment_id']:<20s} {fname:<45s} {label}")

    print(f"\n  Total processing time: {elapsed:.1f} seconds")
    print(f"\n  Output files:")
    print(f"    Models:         models/")
    print(f"    Visualizations: output/")
    print(f"    Feature cache:  feature_cache/")
    print("=" * 60)
    print("  Pipeline complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
