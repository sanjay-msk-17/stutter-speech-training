"""
svm_classifier.py
SVM classifier with RBF kernel for stutter class prediction.
Uses GridSearchCV for hyperparameter tuning.
"""

import numpy as np
import joblib
import os
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import GridSearchCV, cross_val_score
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score,
    precision_score, recall_score, f1_score
)
import warnings
warnings.filterwarnings('ignore')

MODEL_DIR = "models"
SVM_MODEL_PATH = os.path.join(MODEL_DIR, "svm_model.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")

STUTTER_CLASSES = [
    'Fluent Speech', 'Block', 'Prolongation',
    'Sound Repetition', 'Word Repetition', 'Interjection',
]


def train_svm(feature_matrix, pseudo_labels):
    """
    Train an SVM classifier with RBF kernel and GridSearchCV.

    Args:
        feature_matrix: numpy array (N, 47)
        pseudo_labels: list of string labels

    Returns:
        tuple: (model, scaler, label_encoder, results_dict)
    """
    print("\n" + "=" * 60)
    print("STEP 8: SVM Classifier Training")
    print("=" * 60)

    # Clean features
    feature_matrix = np.nan_to_num(feature_matrix, nan=0.0, posinf=0.0, neginf=0.0)

    # Encode labels
    le = LabelEncoder()
    le.fit(STUTTER_CLASSES)
    y = le.transform(pseudo_labels)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(feature_matrix)

    print(f"\n  Training samples: {len(y)}")
    print(f"  Feature dimensions: {X_scaled.shape[1]}")
    print(f"  Classes: {list(le.classes_)}")

    # Grid search for hyperparameter tuning
    # Use two grids: one for RBF (needs gamma), one for linear (no gamma)
    param_grid = [
        {
            'C': [0.1, 1, 10, 100],
            'gamma': ['scale', 'auto', 0.01, 0.1],
            'kernel': ['rbf'],
        },
        {
            'C': [0.01, 0.1, 1, 10],
            'kernel': ['linear'],
        },
    ]

    print("\n  Running GridSearchCV (5-fold CV)...")
    svm = SVC(random_state=42, probability=True, class_weight='balanced')
    grid_search = GridSearchCV(
        svm, param_grid,
        cv=5,
        scoring='f1_weighted',
        n_jobs=-1,
        verbose=0,
        refit=True,
    )
    grid_search.fit(X_scaled, y)

    best_model = grid_search.best_estimator_
    print(f"  Best parameters: {grid_search.best_params_}")
    print(f"  Best CV F1 score: {grid_search.best_score_:.4f}")

    # Cross-validation scores
    cv_scores = cross_val_score(best_model, X_scaled, y, cv=5, scoring='accuracy')
    print(f"  CV Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")

    # Full training set evaluation
    y_pred = best_model.predict(X_scaled)

    accuracy = accuracy_score(y, y_pred)
    precision = precision_score(y, y_pred, average='weighted', zero_division=0)
    recall = recall_score(y, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y, y_pred, average='weighted', zero_division=0)

    print(f"\n  --- Training Set Metrics ---")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")

    # Classification report
    unique_labels = np.unique(y)
    target_names = le.inverse_transform(unique_labels)
    report = classification_report(y, y_pred, labels=unique_labels, target_names=target_names, zero_division=0)
    print(f"\n  Classification Report:")
    print(report)

    # Confusion matrix
    cm = confusion_matrix(y, y_pred)

    # Save models
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(best_model, SVM_MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(le, ENCODER_PATH)
    print(f"  Models saved to: {MODEL_DIR}/")

    results = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'confusion_matrix': cm,
        'classification_report': report,
        'best_params': grid_search.best_params_,
        'cv_accuracy': cv_scores.mean(),
        'cv_std': cv_scores.std(),
        'y_true': y,
        'y_pred': y_pred,
        'label_encoder': le,
    }

    return best_model, scaler, le, results


def predict(feature_vector, model=None, scaler=None, le=None):
    """
    Predict stutter class for a single feature vector.

    Args:
        feature_vector: numpy array (47,)
        model, scaler, le: optional pre-loaded components

    Returns:
        predicted class label (string)
    """
    if model is None:
        model = joblib.load(SVM_MODEL_PATH)
    if scaler is None:
        scaler = joblib.load(SCALER_PATH)
    if le is None:
        le = joblib.load(ENCODER_PATH)

    feature_vector = np.nan_to_num(feature_vector.reshape(1, -1))
    X_scaled = scaler.transform(feature_vector)
    y_pred = model.predict(X_scaled)
    return le.inverse_transform(y_pred)[0]
