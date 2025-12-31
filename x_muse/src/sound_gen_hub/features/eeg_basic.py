"""Basic EEG feature extraction."""

import numpy as np
from ..models import SampleChunk, FeatureVector


def compute_basic_eeg_features(chunk: SampleChunk) -> FeatureVector:
    """
    Compute basic statistical features from an EEG chunk.
    
    Features computed per channel:
    - Mean
    - Standard deviation
    - Mean absolute value
    
    Args:
        chunk: SampleChunk containing EEG data
        
    Returns:
        FeatureVector with computed features
    """
    data = chunk.data  # shape: (n_channels, n_samples)
    
    # Compute features per channel
    means = data.mean(axis=1)
    stds = data.std(axis=1)
    abs_means = np.abs(data).mean(axis=1)
    
    return FeatureVector.from_meta(
        meta=chunk.meta,
        t_start=float(chunk.timestamps[0]),
        t_end=float(chunk.timestamps[-1]),
        features={
            "eeg_mean": means.tolist(),
            "eeg_std": stds.tolist(),
            "eeg_abs_mean": abs_means.tolist(),
        }
    )
