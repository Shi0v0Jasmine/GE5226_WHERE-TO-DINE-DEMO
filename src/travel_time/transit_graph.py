"""
Transit Graph Backend (Manual Subway + Bus Network)
====================================================

Hand-built or GTFS-based transit graph for NYC subway and bus system.

This is a RESERVE backend. Requires:
    - GTFS feed from MTA (https://new.mta.info/developers), OR
    - Hand-built station graph with transfer times

GTFS files needed:
    - stops.txt        (station locations)
    - stop_times.txt   (arrival/departure times)
    - transfers.txt    (transfer times between stations)
    - routes.txt       (route info)

Usage (future):
    from src.travel_time.transit_graph import TransitGraph
    tt = TransitGraph(
        gtfs_path='data/transit/mta_gtfs',
        transfer_penalty=5.0,  # minutes
        wait_penalty=5.0,       # average wait time
    )
    matrix = tt.matrix(origins, destinations)

Architecture (for Codex implementation):
--------------------------------------------
1. Load GTFS data into pandas DataFrames
2. Build station graph: nodes = stops, edges = (route segment + dwell + wait)
3. Add walking edges between nearby stops (transfer)
4. Add origin/destination edges: walk from user location to nearest station(s)
5. Run Dijkstra on the combined graph

Cost estimation (for GTFS approach):
    - Download:  MTA GTFS is free (https://new.mta.info/developers)
    - Parse:     ~2-3 hours of Python work
    - Graph:     ~1 hour
    - Total:     ~4 hours (one focused session)

Author: Where to DINE Project
Date: 2026-06-26
Status: RESERVED (not yet implemented)
"""

import numpy as np
from typing import List, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TransitGraph:
    """
    NYC transit network graph (placeholder for GTFS or hand-built implementation).

    Parameters
    ----------
    gtfs_path : str, optional
        Path to extracted GTFS directory. If not found, falls back to proxy.
    transfer_penalty : float
        Minutes added for each transfer between lines.
    wait_penalty : float
        Average waiting time at station (minutes).
    """

    def __init__(
        self,
        gtfs_path: Optional[str] = None,
        transfer_penalty: float = 5.0,
        wait_penalty: float = 5.0,
        **kwargs
    ):
        self.gtfs_path = gtfs_path or "data/transit/mta_gtfs"
        self.transfer_penalty = transfer_penalty
        self.wait_penalty = wait_penalty
        self._graph = None
        self._fallback = None

    def _load_gtfs(self):
        """Load GTFS data and build transit graph. PLACEHOLDER."""
        # TODO: Implement by Codex
        # Steps:
        # 1. Read stops.txt, stop_times.txt, transfers.txt, routes.txt
        # 2. Build directed graph: nodes = stop_id, edges = (next_stop, travel_time)
        # 3. Add transfer edges between stops at same station (different routes)
        # 4. Cache graph
        return None

    def _get_fallback(self):
        """Get proxy fallback."""
        if self._fallback is None:
            from .proxy_backend import ProxyTravelTime
            self._fallback = ProxyTravelTime(mode='transit')
        return self._fallback

    def matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]]
    ) -> np.ndarray:
        """
        Compute transit travel time matrix.

        Returns minutes. Falls back to proxy if GTFS not available.
        """
        # TODO: Implement by Codex
        # 1. Find nearest station(s) for each origin/destination
        # 2. Add walking edges from origin to station(s) (use haversine + walk speed)
        # 3. Run Dijkstra from each origin-station to all destination-stations
        # 4. Add walking time from destination-station to destination
        # 5. Return matrix

        logger.warning("TransitGraph not yet implemented, using proxy fallback")
        return self._get_fallback().matrix(origins, destinations)

    def single(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> float:
        mat = self.matrix([origin], [destination])
        return float(mat[0, 0])

    def is_available(self) -> bool:
        """Check if GTFS data is available."""
        return Path(self.gtfs_path).exists()

    def info(self) -> dict:
        return {
            'type': 'transit',
            'gtfs_path': self.gtfs_path,
            'gtfs_exists': Path(self.gtfs_path).exists() if self.gtfs_path else False,
            'description': 'NYC subway + bus network via GTFS (manual implementation needed)',
            'note': 'Requires: GTFS download from MTA + ~4 hours of implementation',
            'transfer_penalty': self.transfer_penalty,
            'wait_penalty': self.wait_penalty,
        }
