"""
Travel Time Calculator - Main Interface
=========================================

Unified travel time computation for Where to DINE.

Supports multiple backends:
- proxy:      Line-of-sight distance + mode coefficient (active, no dependencies)
- osmnx:      Real street network via OSMnx (requires local graph)
- google:     Google Maps Distance Matrix API (requires API key)
- transit:    Manual subway/bus graph (requires GTFS or hand-built graph)

Usage:
    from src.travel_time import TravelTimeCalculator
    
    # Default: proxy mode (no dependencies)
    tt = TravelTimeCalculator(mode='transit', backend='proxy')
    matrix = tt.matrix(origins, destinations)
    
    # With OSMnx (offline real network)
    tt = TravelTimeCalculator(mode='walk', backend='osmnx')
    matrix = tt.matrix(origins, destinations)
    
    # With Google API (online, requires key)
    tt = TravelTimeCalculator(mode='transit', backend='google')
    matrix = tt.matrix(origins, destinations)

Author: Where to DINE Project
Date: 2026-06-26
"""

from typing import List, Tuple, Optional, Literal
import numpy as np

from .proxy_backend import ProxyTravelTime
from .osmnx_backend import OSMnxTravelTime
from .google_maps_backend import GoogleMapsTravelTime

BACKENDS = {
    'proxy': ProxyTravelTime,
    'osmnx': OSMnxTravelTime,
    'google': GoogleMapsTravelTime,
}


class BackendUnavailableError(RuntimeError):
    """Raised when a requested routing backend cannot be used."""


class TravelTimeCalculator:
    """
    Unified travel time calculator with pluggable backends.

    Parameters
    ----------
    mode : str
        'walk' | 'bike' | 'drive' | 'transit'
    backend : str
        'proxy' | 'osmnx' | 'google' | 'transit'
    graph_path : str, optional
        Path to pre-downloaded OSMnx graph (for osmnx backend).
    api_key : str, optional
        Google Maps API key (for google backend).
    reference_point : Tuple[float, float], optional
        (lat, lon) reference point for proxy mode. Default: Times Square.
    """

    def __init__(
        self,
        mode: Literal['walk', 'bike', 'drive', 'transit'] = 'transit',
        backend: Literal['proxy', 'osmnx', 'google', 'transit'] = 'proxy',
        graph_path: Optional[str] = None,
        api_key: Optional[str] = None,
        reference_point: Tuple[float, float] = (40.7580, -73.9855),  # Times Square
        allow_fallback: bool = True,
    ):
        if backend not in BACKENDS:
            raise ValueError(f"Unknown backend: {backend}. Choose from: {list(BACKENDS.keys())}")
        
        backend_cls = BACKENDS[backend]
        self.backend = backend_cls(
            mode=mode,
            graph_path=graph_path,
            api_key=api_key,
            reference_point=reference_point,
            allow_fallback=allow_fallback,
        )
        self.mode = mode
        self.requested_backend = backend
        self.allow_fallback = allow_fallback
        self.fallback_reason = None
        self.effective_backend = backend

        if not self.backend.is_available():
            reason = self.backend.info().get('unavailable_reason') or (
                f"{backend} backend is not configured"
            )
            if not allow_fallback:
                raise BackendUnavailableError(reason)
            self.backend = ProxyTravelTime(mode=mode, reference_point=reference_point)
            self.effective_backend = 'proxy'
            self.fallback_reason = reason

    def matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]]
    ) -> np.ndarray:
        """
        Compute travel time matrix from origins to destinations.

        Parameters
        ----------
        origins : list of (lat, lon)
        destinations : list of (lat, lon)

        Returns
        -------
        np.ndarray, shape (n_origins, n_destinations)
            Travel time in minutes.
        """
        try:
            matrix = self.backend.matrix(origins, destinations)
        except RuntimeError as exc:
            if not self.allow_fallback:
                raise BackendUnavailableError(str(exc)) from exc
            raise
        backend_info = self.backend.info()
        if backend_info.get('fallback_used'):
            if not self.allow_fallback:
                raise BackendUnavailableError(
                    backend_info.get('fallback_reason') or
                    f"{self.requested_backend} routing failed"
                )
            self.effective_backend = 'proxy'
            self.fallback_reason = backend_info.get('fallback_reason')
        return matrix

    def single(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float]
    ) -> float:
        """
        Compute travel time for a single origin-destination pair.

        Returns
        -------
        float
            Travel time in minutes.
        """
        mat = self.matrix([origin], [destination])
        return float(mat[0, 0])

    def is_available(self) -> bool:
        """Check if the selected backend is ready to use."""
        return self.backend.is_available()

    def info(self) -> dict:
        """Return backend info and status."""
        return {
            'requested_backend': self.requested_backend,
            'effective_backend': self.effective_backend,
            'mode': self.mode,
            'available': self.is_available(),
            'is_estimate': self.effective_backend == 'proxy',
            'fallback_reason': self.fallback_reason,
            'details': self.backend.info(),
        }
