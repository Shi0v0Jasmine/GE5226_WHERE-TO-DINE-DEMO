"""
Travel Time Calculator Package
==============================

Pluggable travel time computation with multiple backends.

Usage:
    from src.travel_time import TravelTimeCalculator
    
    tt = TravelTimeCalculator(mode='transit', backend='proxy')
    matrix = tt.matrix(origins, destinations)

Backends:
    proxy  : Line-of-sight distance + mode decay (default, no dependencies)
    osmnx  : Real street network via OpenStreetMap (requires osmnx + graph)
    google : Google Maps Distance Matrix API (requires API key + billing)
    transit: NYC subway + bus via GTFS (requires manual implementation)

See travel_time_calculator.py for full documentation.
"""

from .travel_time_calculator import TravelTimeCalculator, BackendUnavailableError

__all__ = ['TravelTimeCalculator', 'BackendUnavailableError']
