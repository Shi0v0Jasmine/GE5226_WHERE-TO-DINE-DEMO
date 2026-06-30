"""
OSMnx Travel Time Backend (Offline Street Network)
====================================================

Real travel time computation using OpenStreetMap network data via OSMnx.

Requires:
    pip install osmnx networkx
    Pre-downloaded NYC graph (see scripts/download_nyc_network.py)

Usage:
    from src.travel_time.osmnx_backend import OSMnxTravelTime
    tt = OSMnxTravelTime(mode='walk', graph_path='data/networks/nyc_walk.graphml')
    matrix = tt.matrix(origins, destinations)

Note:
    This is a RESERVE backend. The graph is large (~500 MB for NYC).
    Activate only when osmnx is installed and the graph is downloaded.

Author: Where to DINE Project
Date: 2026-06-26
"""

import numpy as np
from typing import List, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class OSMnxTravelTime:
    """
    OSMnx-based travel time calculator.

    Parameters
    ----------
    mode : str
        'walk' | 'bike' | 'drive' | 'transit'
        Note: 'transit' is NOT supported by OSMnx natively.
              For transit, use Proxy or Google backend.
    graph_path : str, optional
        Path to OSMnx graphml file. If not found, falls back to proxy.
    """

    def __init__(self, mode='walk', graph_path=None, allow_fallback=True, **kwargs):
        self.mode = mode
        self.graph_path = graph_path or f"data/networks/nyc_{mode}.graphml"
        self.allow_fallback = allow_fallback
        self._G = None
        self._fallback = None
        self.fallback_used = False
        self.fallback_reason = None

    def _load_graph(self):
        """Lazy-load the OSMnx graph."""
        if self._G is not None:
            return self._G

        try:
            import osmnx as ox
            import networkx as nx

            if not Path(self.graph_path).exists():
                logger.warning(f"Graph not found: {self.graph_path}")
                return None

            logger.info(f"Loading OSMnx graph from {self.graph_path}...")
            G = ox.load_graphml(self.graph_path)

            # Ensure travel time attribute exists
            if 'travel_time' not in next(iter(G.edges(data=True)))[2]:
                # Add travel time based on length and speed
                speed_kmh = {
                    'walk': 5.0,
                    'bike': 15.0,
                    'drive': 30.0,
                }.get(self.mode, 5.0)
                speed_mps = speed_kmh * 1000 / 3600
                for u, v, k, data in G.edges(keys=True, data=True):
                    length_m = data.get('length', 0)
                    data['travel_time'] = length_m / speed_mps

            self._G = G
            return G

        except ImportError:
            logger.warning("osmnx not installed, falling back to proxy")
            return None

    def _get_fallback(self):
        """Get fallback proxy backend if OSMnx is unavailable."""
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
        Compute travel time matrix using OSMnx street network.

        Returns minutes.
        """
        G = self._load_graph()

        if G is None:
            self.fallback_used = True
            self.fallback_reason = f"OSMnx graph unavailable: {self.graph_path}"
            if not self.allow_fallback:
                raise RuntimeError(self.fallback_reason)
            logger.warning("%s; using proxy fallback", self.fallback_reason)
            return self._get_fallback().matrix(origins, destinations)

        try:
            import osmnx as ox
            import networkx as nx

            # Find nearest nodes for all origins and destinations
            orig_nodes = [ox.nearest_nodes(G, lon=lon, lat=lat) for lat, lon in origins]
            dest_nodes = [ox.nearest_nodes(G, lon=lon, lat=lat) for lat, lon in destinations]

            n_orig = len(origins)
            n_dest = len(destinations)
            mat = np.full((n_orig, n_dest), np.inf)

            # Compute all pairs shortest paths (Dijkstra from each origin)
            for i, on in enumerate(orig_nodes):
                try:
                    lengths = nx.single_source_dijkstra_path_length(
                        G, on, weight='travel_time'
                    )
                    for j, dn in enumerate(dest_nodes):
                        if dn in lengths:
                            mat[i, j] = lengths[dn] / 60.0  # seconds → minutes
                except nx.NetworkXError:
                    pass

            # Replace any remaining inf with proxy fallback
            if np.isinf(mat).any():
                self.fallback_used = True
                self.fallback_reason = (
                    f"{np.isinf(mat).sum()} OD pairs were unreachable in the OSMnx graph"
                )
                if not self.allow_fallback:
                    raise RuntimeError(self.fallback_reason)
                logger.warning("%s; using proxy", self.fallback_reason)
                proxy_mat = self._get_fallback().matrix(origins, destinations)
                mat = np.where(np.isinf(mat), proxy_mat, mat)

            return mat

        except Exception as e:
            if not self.allow_fallback:
                raise
            self.fallback_used = True
            self.fallback_reason = f"OSMnx computation failed: {e}"
            logger.warning("%s; using proxy fallback", self.fallback_reason)
            return self._get_fallback().matrix(origins, destinations)

    def single(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> float:
        mat = self.matrix([origin], [destination])
        return float(mat[0, 0])

    def is_available(self) -> bool:
        """Check if OSMnx graph is available."""
        try:
            import osmnx
            return self.mode in {'walk', 'bike', 'drive'} and Path(self.graph_path).exists()
        except ImportError:
            return False

    def info(self) -> dict:
        return {
            'type': 'osmnx',
            'mode': self.mode,
            'graph_path': self.graph_path,
            'graph_exists': Path(self.graph_path).exists() if self.graph_path else False,
            'description': 'Real street network via OpenStreetMap + OSMnx',
            'note': 'Requires: pip install osmnx networkx; download graph first',
            'fallback_used': self.fallback_used,
            'fallback_reason': self.fallback_reason,
            'unavailable_reason': (
                None if self.is_available()
                else f"OSMnx graph or dependency unavailable for mode={self.mode}"
            ),
        }
