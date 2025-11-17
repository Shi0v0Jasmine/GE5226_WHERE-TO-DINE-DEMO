"""
Clustering Module
=================

HDBSCAN clustering for restaurant locations and taxi drop-off points.

Author: Your Name
Date: 2025-11-09
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import hdbscan
from sklearn.metrics import silhouette_score, davies_bouldin_score
from typing import Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HDBSCANClustering:
    """
    Wrapper class for HDBSCAN clustering with validation metrics.
    """

    def __init__(self,
                 min_cluster_size: int = 30,
                 min_samples: int = 10,
                 cluster_selection_epsilon: float = 200,
                 metric: str = 'euclidean',
                 cluster_selection_method: str = 'eom'):
        """
        Initialize HDBSCAN clusterer.

        Parameters:
        -----------
        min_cluster_size : int
            Minimum number of points to form a cluster
        min_samples : int
            Conservative density estimate parameter
        cluster_selection_epsilon : float
            Distance threshold (in same units as data - typically meters after projection)
        metric : str
            Distance metric (use 'euclidean' for projected coordinates)
        cluster_selection_method : str
            'eom' (Excess of Mass) or 'leaf'
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.cluster_selection_epsilon = cluster_selection_epsilon
        self.metric = metric
        self.cluster_selection_method = cluster_selection_method

        self.clusterer = None
        self.labels_ = None
        self.n_clusters_ = None
        self.validation_scores_ = {}

    def fit(self, X: np.ndarray) -> np.ndarray:
        """
        Fit HDBSCAN clustering to data.

        Parameters:
        -----------
        X : np.ndarray
            Coordinates array of shape (n_samples, 2)
            Should be in projected CRS (meters)

        Returns:
        --------
        np.ndarray
            Cluster labels (noise points labeled as -1)
        """
        logger.info(f"Fitting HDBSCAN on {len(X)} points...")

        self.clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            cluster_selection_epsilon=self.cluster_selection_epsilon,
            metric=self.metric,
            cluster_selection_method=self.cluster_selection_method
        )

        self.labels_ = self.clusterer.fit_predict(X)
        self.n_clusters_ = len(set(self.labels_)) - (1 if -1 in self.labels_ else 0)

        logger.info(f"Found {self.n_clusters_} clusters")
        logger.info(f"Noise points: {(self.labels_ == -1).sum()}")

        return self.labels_

    def validate(self, X: np.ndarray, labels: Optional[np.ndarray] = None) -> dict:
        """
        Calculate validation metrics for clustering.

        Parameters:
        -----------
        X : np.ndarray
            Coordinates array
        labels : np.ndarray, optional
            Cluster labels. If None, uses self.labels_

        Returns:
        --------
        dict
            Dictionary of validation metrics
        """
        if labels is None:
            labels = self.labels_

        if labels is None:
            raise ValueError("No labels available. Run fit() first.")

        # Exclude noise points
        valid_mask = labels != -1
        X_valid = X[valid_mask]
        labels_valid = labels[valid_mask]

        n_clusters = len(set(labels_valid))

        if n_clusters < 2:
            logger.warning("Less than 2 clusters found, cannot compute validation metrics")
            return {
                'n_clusters': n_clusters,
                'n_noise': (labels == -1).sum(),
                'silhouette_score': None,
                'davies_bouldin_score': None
            }

        # Silhouette Score (higher is better, range [-1, 1])
        sil_score = silhouette_score(X_valid, labels_valid)

        # Davies-Bouldin Score (lower is better)
        db_score = davies_bouldin_score(X_valid, labels_valid)

        self.validation_scores_ = {
            'n_clusters': n_clusters,
            'n_noise': (labels == -1).sum(),
            'silhouette_score': sil_score,
            'davies_bouldin_score': db_score,
            'noise_ratio': (labels == -1).sum() / len(labels)
        }

        logger.info(f"Validation Metrics:")
        logger.info(f"  Silhouette Score: {sil_score:.3f} (> 0.3 is good)")
        logger.info(f"  Davies-Bouldin Score: {db_score:.3f} (< 1.5 is good)")
        logger.info(f"  Noise Ratio: {self.validation_scores_['noise_ratio']:.2%}")

        return self.validation_scores_


def cluster_restaurants(gdf_restaurants: gpd.GeoDataFrame,
                        config: dict) -> gpd.GeoDataFrame:
    """
    Cluster restaurant locations using HDBSCAN.

    Parameters:
    -----------
    gdf_restaurants : gpd.GeoDataFrame
        Restaurant GeoDataFrame (must be in WGS84)
    config : dict
        Configuration dictionary with clustering parameters

    Returns:
    --------
    gpd.GeoDataFrame
        GeoDataFrame with added 'cluster_id' column
    """
    logger.info("Starting restaurant clustering...")

    # Project to meters
    gdf_proj = gdf_restaurants.to_crs(config['geographic']['crs']['projected'])

    # Extract coordinates
    coords = np.column_stack([gdf_proj.geometry.x, gdf_proj.geometry.y])

    # Initialize clusterer
    params = config['clustering']['restaurants']
    clusterer = HDBSCANClustering(
        min_cluster_size=params['min_cluster_size'],
        min_samples=params['min_samples'],
        cluster_selection_epsilon=params['cluster_selection_epsilon'],
        metric=params['metric'],
        cluster_selection_method=params['cluster_selection_method']
    )

    # Fit
    labels = clusterer.fit(coords)

    # Validate
    metrics = clusterer.validate(coords)

    # Add cluster IDs to GeoDataFrame
    gdf_proj['cluster_id'] = labels

    # Transform back to WGS84
    gdf_result = gdf_proj.to_crs(config['geographic']['crs']['wgs84'])

    logger.info("Restaurant clustering complete!")

    return gdf_result, metrics


def cluster_taxi_dropoffs(gdf_taxi: gpd.GeoDataFrame,
                          config: dict,
                          weight_column: str = 'weight') -> Tuple[gpd.GeoDataFrame, dict]:
    """
    Cluster taxi drop-off locations using HDBSCAN.

    Parameters:
    -----------
    gdf_taxi : gpd.GeoDataFrame
        Taxi drop-off GeoDataFrame (must be in WGS84)
    config : dict
        Configuration dictionary
    weight_column : str
        Column containing temporal weights

    Returns:
    --------
    tuple
        (GeoDataFrame with cluster_id, validation metrics dict)
    """
    logger.info("Starting taxi drop-off clustering...")

    # Project to meters
    gdf_proj = gdf_taxi.to_crs(config['geographic']['crs']['projected'])

    # Extract coordinates
    coords = np.column_stack([gdf_proj.geometry.x, gdf_proj.geometry.y])

    # Note: Standard HDBSCAN doesn't use weights directly
    # For weighted clustering, you could:
    # 1. Duplicate points proportional to weight (simplified)
    # 2. Use custom distance metric (advanced)
    # 3. Pre-aggregate to grid with weights (H3 hexagons)
    # For now, we'll note the limitation

    logger.warning("Standard HDBSCAN doesn't use sample weights. "
                   "Consider H3 aggregation for incorporating weights.")

    # Initialize clusterer
    params = config['clustering']['taxi']
    clusterer = HDBSCANClustering(
        min_cluster_size=params['min_cluster_size'],
        min_samples=params['min_samples'],
        cluster_selection_epsilon=params['cluster_selection_epsilon'],
        metric=params['metric'],
        cluster_selection_method=params['cluster_selection_method']
    )

    # Fit
    labels = clusterer.fit(coords)

    # Validate
    metrics = clusterer.validate(coords)

    # Add cluster IDs
    gdf_proj['cluster_id'] = labels

    # Transform back to WGS84
    gdf_result = gdf_proj.to_crs(config['geographic']['crs']['wgs84'])

    logger.info("Taxi clustering complete!")

    return gdf_result, metrics


if __name__ == "__main__":
    # Test with synthetic data
    from src.utils.config_loader import load_config

    config = load_config()

    # Generate synthetic restaurant data
    np.random.seed(42)
    n_points = 1000

    # Create 3 clusters
    cluster1 = np.random.randn(300, 2) * 0.002 + [-73.99, 40.75]
    cluster2 = np.random.randn(300, 2) * 0.002 + [-73.98, 40.76]
    cluster3 = np.random.randn(300, 2) * 0.002 + [-74.01, 40.74]
    noise = np.random.rand(100, 2) * 0.1 + [-74.0, 40.7]

    coords = np.vstack([cluster1, cluster2, cluster3, noise])

    # Create GeoDataFrame
    from shapely.geometry import Point
    gdf = gpd.GeoDataFrame(
        {'name': [f'Restaurant_{i}' for i in range(len(coords))]},
        geometry=[Point(lon, lat) for lon, lat in coords],
        crs="EPSG:4326"
    )

    # Cluster
    gdf_clustered, metrics = cluster_restaurants(gdf, config)

    print(f"Clustering results: {metrics}")
    print(f"Cluster distribution:\n{gdf_clustered['cluster_id'].value_counts()}")
