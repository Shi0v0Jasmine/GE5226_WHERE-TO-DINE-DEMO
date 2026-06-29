"""
Proxy Travel Time Backend
=========================

Lightweight, dependency-free backend using line-of-sight distance
with mode-specific decay coefficients.

No external API, no large graph downloads, no Python GIS libraries.

This is the **default active backend**.

Usage:
    from src.travel_time.proxy_backend import ProxyTravelTime
    tt = ProxyTravelTime(mode='transit')
    matrix = tt.matrix(origins, destinations)

Author: Where to DINE Project
Date: 2026-06-26
"""

import numpy as np
from typing import List, Tuple, Optional
import math

# Mode-specific decay coefficients (empirically tuned for NYC)
# Larger coefficient = faster decay (shorter effective reach)
MODE_COEFFICIENTS = {
    'walk':    0.15,  # ~5 km/h, 30 min ~ 2.5 km reach
    'bike':    0.07,  # ~15 km/h, 30 min ~ 7.5 km reach
    'drive':   0.05,  # ~25 km/h avg, 30 min ~ 12.5 km reach (NYC traffic)
    'transit': 0.04,  # ~30 km/h avg (subway), 30 min ~ 15 km reach
}

# Manhattan distance conversion factor for haversine
EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute great-circle distance between two points in km.
    """
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


class ProxyTravelTime:
    """
    Proxy travel time calculator using line-of-sight distance + mode decay.
    """

    def __init__(self, mode='transit', reference_point=None, **kwargs):
        self.mode = mode
        self.coeff = MODE_COEFFICIENTS.get(mode, MODE_COEFFICIENTS['transit'])
        self.reference_point = reference_point  # (lat, lon) for reference, not used in calculation

    def matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]]
    ) -> np.ndarray:
        """
        Compute travel time proxy matrix.

        Returns minutes based on exp(-coeff * distance_km) → 100 at 0 km, ~0 at far.
        We convert back to travel time estimate: 100 → 0 min, 0 → 30 min (hard cap).
        """
        n_orig = len(origins)
        n_dest = len(destinations)
        mat = np.zeros((n_orig, n_dest))

        for i, (lat1, lon1) in enumerate(origins):
            for j, (lat2, lon2) in enumerate(destinations):
                dist_km = haversine_distance(lat1, lon1, lat2, lon2)
                # Exponential decay: 100 at 0 km, decays with coeff
                accessibility = 100.0 * np.exp(-self.coeff * dist_km)
                # Convert accessibility score back to travel time estimate (minutes)
                # 100 → 0 min, 50 → ~10 min, 20 → ~20 min, 5 → ~30 min
                # Using: time = -ln(access/100) / (coeff * speed_factor)
                # Simpler: direct mapping from distance to time estimate
                if dist_km < 0.1:
                    travel_time = 2.0  # 2 minutes for very close
                else:
                    # Mode-specific speed (km/min)
                    speed_km_min = {
                        'walk': 5.0 / 60,
                        'bike': 15.0 / 60,
                        'drive': 25.0 / 60,
                        'transit': 30.0 / 60,
                    }.get(self.mode, 30.0 / 60)
                    
                    # Base time + penalty for distance
                    travel_time = dist_km / speed_km_min
                    
                    # Add mode-specific overhead (wait time, transfer, etc.)
                    overhead = {
                        'walk': 0,
                        'bike': 0,
                        'drive': 5,    # parking search
                        'transit': 8,  # wait + transfer buffer
                    }.get(self.mode, 0)
                    
                    travel_time += overhead
                    travel_time = min(travel_time, 60.0)  # hard cap at 60 min
                
                mat[i, j] = travel_time
        return mat

    def single(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> float:
        mat = self.matrix([origin], [destination])
        return float(mat[0, 0])

    def is_available(self) -> bool:
        return True

    def info(self) -> dict:
        return {
            'type': 'proxy',
            'mode': self.mode,
            'coefficient': self.coeff,
            'description': 'Line-of-sight distance with mode-specific decay',
        }
