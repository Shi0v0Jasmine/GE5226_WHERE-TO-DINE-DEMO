"""
Configuration Loader Utility
=============================

Loads configuration from YAML files.

Author: Your Name
Date: 2025-11-09
"""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Parameters:
    -----------
    config_path : str
        Path to configuration YAML file (relative to project root)

    Returns:
    --------
    dict
        Configuration dictionary

    Example:
    --------
    >>> config = load_config()
    >>> print(config['clustering']['restaurants']['min_cluster_size'])
    30
    """
    # Get project root (assuming this file is in src/utils/)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    full_config_path = project_root / config_path

    if not full_config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {full_config_path}")

    with open(full_config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def get_data_path(dataset_key: str, config: Dict[str, Any] = None) -> Path:
    """
    Get full path to dataset from configuration.

    Parameters:
    -----------
    dataset_key : str
        Dot-notation key path (e.g., "interim.taxi_filtered")
    config : dict, optional
        Configuration dictionary. If None, loads default config.

    Returns:
    --------
    pathlib.Path
        Full path to dataset

    Example:
    --------
    >>> path = get_data_path("interim.taxi_filtered")
    >>> print(path)
    /path/to/project/data/interim/taxi_filtered_dining_hours.parquet
    """
    if config is None:
        config = load_config()

    # Navigate nested dictionary using dot notation
    keys = dataset_key.split('.')
    value = config['data']
    for key in keys:
        value = value[key]

    # Get project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent

    return project_root / value


def get_config_value(key_path: str, config: Dict[str, Any] = None) -> Any:
    """
    Get configuration value using dot notation.

    Parameters:
    -----------
    key_path : str
        Dot-notation key path (e.g., "clustering.restaurants.min_cluster_size")
    config : dict, optional
        Configuration dictionary. If None, loads default config.

    Returns:
    --------
    Any
        Configuration value

    Example:
    --------
    >>> min_size = get_config_value("clustering.restaurants.min_cluster_size")
    >>> print(min_size)
    30
    """
    if config is None:
        config = load_config()

    keys = key_path.split('.')
    value = config
    for key in keys:
        value = value[key]

    return value


if __name__ == "__main__":
    # Test configuration loading
    config = load_config()
    print("Configuration loaded successfully!")
    print(f"Project: {config['metadata']['project_name']}")
    print(f"Version: {config['metadata']['version']}")
    print(f"Min cluster size (restaurants): {config['clustering']['restaurants']['min_cluster_size']}")

    # Test path retrieval
    taxi_path = get_data_path("interim.taxi_filtered")
    print(f"Taxi data path: {taxi_path}")
