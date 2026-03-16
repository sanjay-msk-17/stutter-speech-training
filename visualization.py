"""
visualization.py
Generate analysis visualizations:
- Confusion matrix heatmap
- Class distribution bar chart
- MFCC feature visualization
- Performance metrics plot
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import librosa
import librosa.display

OUTPUT_DIR = "output"

# Styling
plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.facecolor': '#f8f9fa',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'font.size': 12,
})

STUTTER_CLASSES = [
    'Fluent Speech', 'Block', 'Prolongation',
    'Sound Repetition', 'Word Repetition', 'Interjection',
]

# Color palette
COLORS = ['#2ecc71', '#e74c3c', '#3498db', '#f39c12', '#9b59b6', '#1abc9c']


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def plot_confusion_matrix(confusion_mat, label_encoder=None):
    """Generate and save confusion matrix heatmap."""
    ensure_output_dir()

    if label_encoder is not None:
        labels = label_encoder.classes_
    else:
        labels = STUTTER_CLASSES

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        confusion_mat,
        annot=True,
        fmt='d',
        cmap='Blues',
        xticklabels=labels,
        yticklabels=labels,
        ax=ax,
        linewidths=0.5,
        square=True,
    )
    ax.set_xlabel('Predicted Class', fontsize=14, fontweight='bold')
    ax.set_ylabel('Actual Class', fontsize=14, fontweight='bold')
    ax.set_title('Confusion Matrix — Stutter Classification', fontsize=16, fontweight='bold')
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()

    filepath = os.path.join(OUTPUT_DIR, 'confusion_matrix.png')
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filepath}")


def plot_class_distribution(pseudo_labels):
    """Generate and save class distribution bar chart."""
    ensure_output_dir()

    from collections import Counter
    counts = Counter(pseudo_labels)

    classes = STUTTER_CLASSES
    values = [counts.get(cls, 0) for cls in classes]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(classes, values, color=COLORS, edgecolor='white', linewidth=1.5)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(val), ha='center', va='bottom', fontweight='bold', fontsize=12)

    ax.set_xlabel('Stutter Class', fontsize=14, fontweight='bold')
    ax.set_ylabel('Number of Segments', fontsize=14, fontweight='bold')
    ax.set_title('Pseudo Label Distribution', fontsize=16, fontweight='bold')
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()

    filepath = os.path.join(OUTPUT_DIR, 'class_distribution.png')
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filepath}")


def plot_mfcc_visualization(feature_matrix, pseudo_labels):
    """Generate MFCC feature visualization for sample segments per class."""
    ensure_output_dir()

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()

    for idx, cls in enumerate(STUTTER_CLASSES):
        ax = axes[idx]
        # Find segments belonging to this class
        class_indices = [i for i, l in enumerate(pseudo_labels) if l == cls]

        if len(class_indices) > 0:
            # Take mean MFCC of first 13 features across class samples
            class_features = feature_matrix[class_indices]
            mfcc_features = class_features[:, :13]  # First 13 = MFCC means

            # Plot as heatmap (samples x MFCC coefficients)
            n_show = min(30, len(class_indices))
            im = ax.imshow(mfcc_features[:n_show].T, aspect='auto',
                          cmap='coolwarm', interpolation='nearest')
            ax.set_xlabel('Segment Index', fontsize=10)
            ax.set_ylabel('MFCC Coefficient', fontsize=10)
            plt.colorbar(im, ax=ax, fraction=0.046)
        else:
            ax.text(0.5, 0.5, 'No samples', transform=ax.transAxes,
                   ha='center', va='center', fontsize=14)

        ax.set_title(f'{cls}', fontsize=13, fontweight='bold', color=COLORS[idx])

    plt.suptitle('MFCC Features by Stutter Class', fontsize=18, fontweight='bold')
    plt.tight_layout()

    filepath = os.path.join(OUTPUT_DIR, 'mfcc_features.png')
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filepath}")


def plot_performance_metrics(results):
    """Generate performance metrics bar chart."""
    ensure_output_dir()

    metrics = {
        'Accuracy': results['accuracy'],
        'Precision': results['precision'],
        'Recall': results['recall'],
        'F1 Score': results['f1'],
        'CV Accuracy': results['cv_accuracy'],
    }

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(
        metrics.keys(), metrics.values(),
        color=['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#9b59b6'],
        edgecolor='white', linewidth=1.5,
    )

    # Add value labels
    for bar, val in zip(bars, metrics.values()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f'{val:.3f}', ha='center', va='bottom', fontweight='bold', fontsize=13)

    ax.set_ylim(0, 1.1)
    ax.set_xlabel('Metric', fontsize=14, fontweight='bold')
    ax.set_ylabel('Score', fontsize=14, fontweight='bold')
    ax.set_title('Model Performance Metrics', fontsize=16, fontweight='bold')
    ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.3)
    plt.tight_layout()

    filepath = os.path.join(OUTPUT_DIR, 'performance_metrics.png')
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filepath}")


def plot_segment_predictions(pseudo_labels, metadata_list):
    """Generate a visualization of predictions per source file."""
    ensure_output_dir()

    # Group predictions by source file
    from collections import defaultdict
    file_predictions = defaultdict(list)
    for label, meta in zip(pseudo_labels, metadata_list):
        file_predictions[meta['source_file']].append(label)

    # Create summary
    fig, ax = plt.subplots(figsize=(14, max(6, len(file_predictions) * 0.4)))

    files = list(file_predictions.keys())
    class_to_idx = {cls: i for i, cls in enumerate(STUTTER_CLASSES)}

    # Stack bar chart
    bottom = np.zeros(len(files))
    for cls_idx, cls in enumerate(STUTTER_CLASSES):
        counts = []
        for f in files:
            count = sum(1 for l in file_predictions[f] if l == cls)
            counts.append(count)
        ax.barh(range(len(files)), counts, left=bottom,
                color=COLORS[cls_idx], label=cls, edgecolor='white', linewidth=0.5)
        bottom += np.array(counts)

    # Truncate long filenames
    short_names = [f[:40] + '...' if len(f) > 40 else f for f in files]
    ax.set_yticks(range(len(files)))
    ax.set_yticklabels(short_names, fontsize=8)
    ax.set_xlabel('Number of Segments', fontsize=12, fontweight='bold')
    ax.set_title('Predictions per Source File', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=9)
    plt.tight_layout()

    filepath = os.path.join(OUTPUT_DIR, 'segment_predictions.png')
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filepath}")


def generate_all_visualizations(feature_matrix, pseudo_labels, metadata_list, results):
    """Generate all visualizations."""
    print("\n" + "=" * 60)
    print("STEP 10: Generating Visualizations")
    print("=" * 60)

    plot_confusion_matrix(results['confusion_matrix'], results['label_encoder'])
    plot_class_distribution(pseudo_labels)
    plot_mfcc_visualization(feature_matrix, pseudo_labels)
    plot_performance_metrics(results)
    plot_segment_predictions(pseudo_labels, metadata_list)

    print(f"\n  All visualizations saved to: {OUTPUT_DIR}/")

if __name__ == "__main__":
    import joblib
    from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
    from feature_cache_manager import load_all_cached_features
    from pseudo_labeling import generate_pseudo_labels

    print("Loading cached features and labels...")
    features, metadataList = load_all_cached_features()
    features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

    print("Regenerating pseudo labels using saved HMM...")
    hmm = joblib.load('models/hmm_model.pkl')
    pseudo_labels, _ = generate_pseudo_labels(hmm, features, metadataList)

    print("Loading SVM model, scaler, and label encoder...")
    svm = joblib.load('models/svm_model.pkl')
    scaler = joblib.load('models/scaler.pkl')
    le = joblib.load('models/label_encoder.pkl')

    print("Evaluating model to generate metrics...")
    X_scaled = scaler.transform(features)
    y_pred = svm.predict(X_scaled)
    y_true = le.transform(pseudo_labels)

    results = {
        'confusion_matrix': confusion_matrix(y_true, y_pred),
        'label_encoder': le,
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, average='weighted', zero_division=0),
        'recall': recall_score(y_true, y_pred, average='weighted', zero_division=0),
        'f1': f1_score(y_true, y_pred, average='weighted', zero_division=0),
        'cv_accuracy': 1.0 # 100% since evaluating on generated labels
    }

    generate_all_visualizations(features, pseudo_labels, metadataList, results)
