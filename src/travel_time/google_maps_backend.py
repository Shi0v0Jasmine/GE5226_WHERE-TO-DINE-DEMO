"""
Google Maps Travel Time Backend (Online API)
=============================================

Real travel time using Google Maps Distance Matrix API.

Supports all modes:
    - driving    (with traffic)
    - walking
    - bicycling
    - transit    (subway + bus + rail)

Requires:
    GOOGLE_MAPS_API_KEY environment variable or api_key parameter

Pricing (2024, per 1000 elements):
    - Distance Matrix: ~$5 USD
    - With traffic:    ~$10 USD

Usage:
    from src.travel_time.google_maps_backend import GoogleMapsTravelTime
    tt = GoogleMapsTravelTime(mode='transit', api_key='YOUR_KEY')
    matrix = tt.matrix(origins, destinations)

Note:
    This is a RESERVE backend. Requires Google Cloud billing.
    Activate only when API key is configured.

Author: Where to DINE Project
Date: 2026-06-26
"""

import numpy as np
from typing import List, Tuple, Optional
import os
import logging

logger = logging.getLogger(__name__)


class GoogleMapsTravelTime:
    """
    Google Maps Distance Matrix API backend.

    Parameters
    ----------
    mode : str
        'walk' -> 'walking', 'drive' -> 'driving', 'transit' -> 'transit', 'bike' -> 'bicycling'
    api_key : str, optional
        Google Maps API key. Falls back to GOOGLE_MAPS_API_KEY env var.
    """

    def __init__(self, mode='transit', api_key=None, **kwargs):
        self.mode = self._map_mode(mode)
        self.api_key = api_key or os.getenv('GOOGLE_MAPS_API_KEY')
        self._fallback = None

    def _map_mode(self, mode: str) -> str:
        """Map internal mode names to Google API mode names."""
        mapping = {
            'walk': 'walking',
            'walking': 'walking',
            'drive': 'driving',
            'driving': 'driving',
            'transit': 'transit',
            'public_transport': 'transit',
            'bike': 'bicycling',
            'bicycling': 'bicycling',
        }
        return mapping.get(mode, 'transit')

    def _get_fallback(self):
        """Get fallback proxy backend if API key is missing."""
        if self._fallback is None:
            from .proxy_backend import ProxyTravelTime
            self._fallback = ProxyTravelTime(mode=self.mode)
        return self._fallback

    def matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]]
    ) -> np.ndarray:
        """
        Compute travel time matrix via Google Maps Distance Matrix API.

        Returns minutes.
        """
        if not self.api_key:
            logger.warning("Google Maps API key not configured, using proxy fallback")
            return self._get_fallback().matrix(origins, destinations)

        try:
            import requests
        except ImportError:
            logger.warning("requests not installed, using proxy fallback")
            return self._get_fallback().matrix(origins, destinations)

        # Google Distance Matrix API
        base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"

        n_orig = len(origins)
        n_dest = len(destinations)
        mat = np.full((n_orig, n_dest), np.inf)

        # Google API limits: max 25 origins or 25 destinations per request
        # We batch in chunks
        ORIGIN_LIMIT = 25
        DEST_LIMIT = 25

        for i_start in range(0, n_orig, ORIGIN_LIMIT):
            i_end = min(i_start + ORIGIN_LIMIT, n_orig)
            orig_chunk = origins[i_start:i_end]
            orig_str = "|".join([f"{lat},{lon}" for lat, lon in orig_chunk])

            for j_start in range(0, n_dest, DEST_LIMIT):
                j_end = min(j_start + DEST_LIMIT, n_dest)
                dest_chunk = destinations[j_start:j_end]
                dest_str = "|".join([f"{lat},{lon}" for lat, lon in dest_chunk])

                params = {
                    'origins': orig_str,
                    'destinations': dest_str,
                    'mode': self.mode,
                    'key': self.api_key,
                }

                # For transit, add departure time (now) for realistic schedules
                if self.mode == 'transit':
                    import time
                    params['departure_time'] = int(time.time())

                try:
                    resp = requests.get(base_url, params=params, timeout=30)
                    data = resp.json()

                    if data.get('status') != 'OK':
                        logger.warning(f"Google API error: {data.get('status')}")
                        continue

                    rows = data.get('rows', [])
                    for i_rel, row in enumerate(rows):
                        elements = row.get('elements', [])
                        for j_rel, elem in enumerate(elements):
                            if elem.get('status') == 'OK':
                                duration_sec = elem['duration']['value']
                                mat[i_start + i_rel, j_start + j_rel] = duration_sec / 60.0

                except Exception as e:
                    logger.warning(f"Google API request failed: {e}")
                    continue

        # Fill any missing values with proxy fallback
        if np.isinf(mat).any():
            logger.warning(f"{np.isinf(mat).sum()} OD pairs failed in Google API, using proxy")
            proxy_mat = self._get_fallback().matrix(origins, destinations)
            mat = np.where(np.isinf(mat), proxy_mat, mat)

        return mat

    def single(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> float:
        mat = self.matrix([origin], [destination])
        return float(mat[0, 0])

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    def info(self) -> dict:
        return {
            'type': 'google',
            'mode': self.mode,
            'api_key_configured': bool(self.api_key),
            'description': 'Google Maps Distance Matrix API (online, paid)',
            'note': 'Requires: GOOGLE_MAPS_API_KEY env var or api_key parameter; billing enabled',
            'pricing_reference': '~$5 per 1000 elements (Distance Matrix)',
        }
