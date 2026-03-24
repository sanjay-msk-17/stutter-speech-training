"""
inference.py - SVM-only inference pipeline for the webapp.
Loads the trained SVM, scaler, and label encoder from the models directory.
Runs: preprocess -> silence removal -> segmentation -> feature extraction -> SVM predict
"""
import os
import sys
import numpy as np
import joblib
import warnings
import io
import tempfile
import subprocess
warnings.filterwarnings('ignore')

# Import local copies of ML pipeline modules (bundled alongside this file for deployment)
from feature_extraction import extract_features
from segmentation import remove_silence, segment_audio

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

_svm_model = None
_scaler = None
_label_encoder = None


def load_models():
    global _svm_model, _scaler, _label_encoder
    if _svm_model is None:
        _svm_model = joblib.load(os.path.join(MODEL_DIR, "svm_model.pkl"))
        _scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
        _label_encoder = joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl"))
    return _svm_model, _scaler, _label_encoder


def preprocess_audio_bytes(audio_bytes: bytes, original_filename: str = "audio.wav") -> tuple:
    """
    Convert uploaded audio bytes to a numpy float32 array at 16kHz mono.
    Handles WAV/WebM/OGG/MP4 via ffmpeg.
    Returns (audio_array, sample_rate)
    """
    import librosa
    ext = os.path.splitext(original_filename)[1].lower() or ".webm"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_in:
        tmp_in.write(audio_bytes)
        tmp_in_path = tmp_in.name

    tmp_wav_path = tmp_in_path.replace(ext, "_converted.wav")

    try:
        # Use ffmpeg to convert to 16kHz mono WAV
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_in_path, "-ar", "16000", "-ac", "1", tmp_wav_path],
            capture_output=True, timeout=60
        )
        if result.returncode != 0:
            # Fallback: try librosa directly
            audio, sr = librosa.load(tmp_in_path, sr=16000, mono=True)
        else:
            audio, sr = librosa.load(tmp_wav_path, sr=16000, mono=True)
    finally:
        try:
            os.unlink(tmp_in_path)
        except Exception:
            pass
        try:
            os.unlink(tmp_wav_path)
        except Exception:
            pass

    # Normalize to [-1, 1]
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val

    return audio.astype(np.float32), sr


def run_inference(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    """
    Full SVM inference pipeline.
    Returns a dict with predicted_class, label_counts, probabilities, duration, etc.
    """
    svm_model, scaler, label_encoder = load_models()

    # Step 1: Preprocess
    audio, sr = preprocess_audio_bytes(audio_bytes, filename)
    duration = len(audio) / sr

    # Step 2: Remove silence (VAD)
    speech_audio = remove_silence(audio, sr)
    speech_duration = len(speech_audio) / sr

    if len(speech_audio) < sr * 0.5:
        return {
            "error": "Audio too short after silence removal",
            "duration": duration,
            "speech_duration": speech_duration,
        }

    # Step 3: Segment (3s, 50% overlap)
    segments = segment_audio(speech_audio, sr)
    if not segments:
        return {"error": "No segments could be created", "duration": duration}

    # Step 4: Extract features
    feature_matrix = []
    for seg in segments:
        feat = extract_features(seg, sr)
        feature_matrix.append(feat)

    feature_matrix = np.array(feature_matrix)
    feature_matrix = np.nan_to_num(feature_matrix, nan=0.0, posinf=0.0, neginf=0.0)

    # Step 5: SVM prediction
    X_scaled = scaler.transform(feature_matrix)
    y_pred = svm_model.predict(X_scaled)
    predicted_labels = label_encoder.inverse_transform(y_pred)

    # Class probabilities (averaged across segments)
    class_probs = None
    if hasattr(svm_model, 'predict_proba'):
        try:
            all_probs = svm_model.predict_proba(X_scaled)
            class_probs = np.mean(all_probs, axis=0)
        except Exception:
            pass

    # Aggregate
    from collections import Counter
    label_counts = dict(Counter(predicted_labels))
    num_segments = len(segments)

    fluent_count = label_counts.get('Fluent Speech', 0)
    fluent_ratio = fluent_count / num_segments

    stutter_counts = {k: v for k, v in label_counts.items() if k != 'Fluent Speech'}
    total_stutter = sum(stutter_counts.values())

    if total_stutter >= 2 or (num_segments <= 3 and total_stutter >= 1):
        sorted_stutters = sorted(stutter_counts.items(), key=lambda x: x[1], reverse=True)
        overall_verdict = sorted_stutters[0][0]
    else:
        overall_verdict = 'Fluent Speech'

    probabilities = {}
    if class_probs is not None:
        class_names = label_encoder.classes_
        probabilities = {name: float(prob) for name, prob in zip(class_names, class_probs)}

    return {
        "predicted_class": overall_verdict,
        "label_counts": label_counts,
        "probabilities": probabilities,
        "duration": duration,
        "speech_duration": speech_duration,
        "num_segments": num_segments,
        "fluent_ratio": fluent_ratio,
    }
