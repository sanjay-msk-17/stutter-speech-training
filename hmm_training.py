"""
hmm_training.py
HMM-GMM temporal modeling using hmmlearn.
Trains a Gaussian HMM with 6 hidden states to discover
temporal speech patterns corresponding to stutter types.
"""

import numpy as np
import joblib
import os
from hmmlearn import hmm
import warnings
warnings.filterwarnings('ignore')

N_HIDDEN_STATES = 6  # One per target stutter class
N_ITER = 150         # EM iterations
RANDOM_STATE = 42
MODEL_PATH = "models/hmm_model.pkl"


def train_hmm(feature_matrix, n_states=N_HIDDEN_STATES, n_iter=N_ITER):
    """
    Train a Gaussian HMM on the feature matrix.

    Uses the Baum-Welch (EM) algorithm to discover hidden temporal
    patterns in speech features.

    Args:
        feature_matrix: numpy array of shape (N_segments, N_features)
        n_states: number of hidden states (default 6)
        n_iter: number of EM iterations

    Returns:
        trained HMM model
    """
    print("\n" + "=" * 60)
    print("STEP 6: HMM-GMM Temporal Modeling")
    print("=" * 60)

    # Replace NaN/Inf values
    feature_matrix = np.nan_to_num(feature_matrix, nan=0.0, posinf=0.0, neginf=0.0)

    print(f"\n  Feature matrix shape: {feature_matrix.shape}")
    print(f"  Hidden states: {n_states}")
    print(f"  Max iterations: {n_iter}")

    # Train Gaussian HMM
    model = hmm.GaussianHMM(
        n_components=n_states,
        covariance_type='diag',     # diag is more stable for high-dim features
        n_iter=n_iter,
        random_state=RANDOM_STATE,
        verbose=False,
        tol=1e-4,
    )

    # Fit on entire feature matrix — treat each row as a single observation
    # We provide lengths to tell the HMM the sequence structure
    # Here we treat the whole dataset as one long sequence
    print("\n  Training HMM (Baum-Welch algorithm)...")
    model.fit(feature_matrix)

    print(f"  Training converged: {model.monitor_.converged}")
    print(f"  Final log-likelihood: {model.score(feature_matrix):.2f}")

    # Save model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"  Model saved to: {MODEL_PATH}")

    return model


def load_hmm_model():
    """Load a previously trained HMM model."""
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None
