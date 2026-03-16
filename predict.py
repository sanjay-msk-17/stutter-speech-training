"""
predict.py
Predict stuttering class for a sample audio file using trained models.

Usage:
    python predict.py <audio_file>
    python predict.py "path/to/audio.wav"
    python predict.py "path/to/audio.mp3"

Supported formats: WAV, MP3, M4A
"""

import os
import sys
import time
import numpy as np
import joblib
import warnings
warnings.filterwarnings('ignore')

from data_preprocessing import load_audio_file
from segmentation import remove_silence, segment_audio
from feature_extraction import extract_features

# Model paths
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
SVM_MODEL_PATH = os.path.join(MODEL_DIR, "svm_model.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")
HMM_MODEL_PATH = os.path.join(MODEL_DIR, "hmm_model.pkl")


def load_models():
    """Load all trained models from disk."""
    print("\n  Loading models...")

    missing = []
    for path, name in [
        (SVM_MODEL_PATH, "SVM model"),
        (SCALER_PATH, "Scaler"),
        (ENCODER_PATH, "Label encoder"),
        (HMM_MODEL_PATH, "HMM model"),
    ]:
        if not os.path.exists(path):
            missing.append(f"    - {name}: {path}")

    if missing:
        print("\n  [ERROR] Missing model files:")
        for m in missing:
            print(m)
        print("\n  Run 'python main.py' first to train the models.")
        sys.exit(1)

    svm_model = joblib.load(SVM_MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    label_encoder = joblib.load(ENCODER_PATH)
    hmm_model = joblib.load(HMM_MODEL_PATH)

    print("  Models loaded successfully!")
    return svm_model, scaler, label_encoder, hmm_model


def predict_audio(filepath):
    """
    Predict stuttering class for a single audio file (processed as a whole).

    Steps:
        1. Load and preprocess audio
        2. Remove silence (VAD)
        3. Segment audio into 3-second windows
        4. Extract features from each segment
        5. Predict class for each segment with SVM
        6. Aggregate predictions

    Args:
        filepath: path to audio file (WAV, MP3, or M4A)

    Returns:
        dict with prediction result
    """
    print("\n" + "=" * 60)
    print("  Stuttering Detection — Single File Prediction")
    print("=" * 60)

    # Validate file
    if not os.path.exists(filepath):
        print(f"\n  [ERROR] File not found: {filepath}")
        sys.exit(1)

    filename = os.path.basename(filepath)
    print(f"\n  Audio file:  {filename}")
    print(f"  Full path:   {filepath}")

    # ---- Step 1: Load audio ----
    print("\n  [1/4] Loading audio...")
    audio, sr = load_audio_file(filepath)
    if audio is None:
        print("  [ERROR] Could not load the audio file!")
        sys.exit(1)

    duration = len(audio) / sr
    print(f"        Duration: {duration:.2f}s | Sample rate: {sr} Hz")

    # ---- Step 2: Remove silence ----
    print("  [2/4] Removing silence...")
    speech_audio = remove_silence(audio, sr)
    speech_duration = len(speech_audio) / sr
    print(f"        Speech duration after VAD: {speech_duration:.2f}s")

    if len(speech_audio) < sr * 0.1:
        print("\n  [ERROR] Audio too short after silence removal.")
        sys.exit(1)

    # ---- Step 3: Segment audio ----
    print("  [3/5] Segmenting audio...")
    segments = segment_audio(speech_audio, sr)
    num_segments = len(segments)
    print(f"        Generated {num_segments} overlapping segments (3s each)")

    if num_segments == 0:
        print("\n  [ERROR] No segments could be created.")
        sys.exit(1)

    # ---- Step 4: Extract features ----
    print("  [4/5] Extracting features per segment...")
    svm_model, scaler, label_encoder, hmm_model = load_models()
    
    feature_matrix = []
    for seg in segments:
        feat = extract_features(seg, sr)
        feature_matrix.append(feat)
        
    feature_matrix = np.array(feature_matrix)
    feature_matrix = np.nan_to_num(feature_matrix, nan=0.0, posinf=0.0, neginf=0.0)
    print(f"        Feature matrix shape: {feature_matrix.shape}")

    # ---- Step 5: Predict ----
    print("  [5/5] Predicting segment classes with SVM...")
    X_scaled = scaler.transform(feature_matrix)

    y_pred = svm_model.predict(X_scaled)
    predicted_labels = label_encoder.inverse_transform(y_pred)

    # Use the SVM's natural argmax predictions. Since the model is now highly balanced
    # and accurate, we can trust its default decision boundary.
    y_pred = svm_model.predict(X_scaled)
    predicted_labels = label_encoder.inverse_transform(y_pred)

    class_probs = None
    if hasattr(svm_model, 'predict_proba'):
        try:
            all_probs = svm_model.predict_proba(X_scaled)
            class_probs = np.mean(all_probs, axis=0)
        except Exception:
            pass

    # Aggregate predictions
    from collections import Counter
    label_counts = Counter(predicted_labels)

    # Determine overall verdict
    fluent_count = label_counts.get('Fluent Speech', 0)
    fluent_ratio = fluent_count / num_segments

    stutter_counts = {k: v for k, v in label_counts.items() if k != 'Fluent Speech'}
    total_stutter_segs = sum(stutter_counts.values())

    # Require at least 2 stutter segments (or 1 if the audio is very short)
    # to avoid a single false positive condemning the entire file.
    if total_stutter_segs >= 2 or (num_segments <= 3 and total_stutter_segs >= 1):
        # Sort stutters by count descending
        sorted_stutters = sorted(stutter_counts.items(), key=lambda x: x[1], reverse=True)
        overall_verdict = sorted_stutters[0][0]
    else:
        overall_verdict = 'Fluent Speech'

    # ---- Results ----
    print("\n" + "=" * 60)
    print("  PREDICTION RESULTS")
    print("=" * 60)

    print(f"\n  Audio file:      {filename}")
    print(f"  Duration:        {duration:.2f}s")
    print(f"  Speech duration: {speech_duration:.2f}s")
    print(f"  Total Segments:  {num_segments}")

    print(f"\n  {'-' * 50}")

    if overall_verdict == 'Fluent Speech':
        print(f"  [OK] OVERALL VERDICT: Fluent Speech (No stutters detected)")
    else:
        print(f"  ! OVERALL VERDICT: Stuttering Detected - {overall_verdict}")

    print(f"  {'-' * 50}")

    print(f"\n  Segment Breakdown:")
    # Sort by frequency
    for label, count in label_counts.most_common():
        pct = count / num_segments
        bar = "#" * int(pct * 33) + "-" * (33 - int(pct * 33))
        marker = " <" if label == overall_verdict else ""
        print(f"    {label:<22s} {count:3d} segs ({pct:5.1%})  {bar}{marker}")

    # Show class probabilities
    if class_probs is not None:
        print(f"\n  Average Class Probabilities (across segments):")
        class_names = label_encoder.classes_
        # Sort by probability descending
        sorted_indices = np.argsort(class_probs)[::-1]
        for idx in sorted_indices:
            prob = class_probs[idx]
            name = class_names[idx]
            bar = "#" * int(prob * 33) + "-" * (33 - int(prob * 33))
            print(f"    {name:<22s} {prob:6.1%}  {bar}")

    print(f"  {'-' * 50}")

    return {
        'filename': filename,
        'duration': duration,
        'speech_duration': speech_duration,
        'predicted_class': overall_verdict,
        'fluent_ratio': fluent_ratio,
        'label_counts': dict(label_counts),
        'probabilities': dict(zip(label_encoder.classes_, class_probs)) if class_probs is not None else None,
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("\n  Usage: python predict.py <audio_file>")
        print("\n  Examples:")
        print('    python predict.py "sample.wav"')
        print('    python predict.py "C:\\path\\to\\audio.mp3"')
        print("\n  Supported formats: WAV, MP3, M4A")
        sys.exit(1)

    audio_path = sys.argv[1]

    # Handle relative paths
    if not os.path.isabs(audio_path):
        audio_path = os.path.join(os.getcwd(), audio_path)

    start = time.time()
    result = predict_audio(audio_path)
    elapsed = time.time() - start

    print(f"\n  Completed in {elapsed:.1f}s\n")
