"""
Data ingestion layer - adapters for F1 data sources.
"""

from .base import DataProvider
from .openf1_client import OpenF1Client

__all__ = ["DataProvider", "OpenF1Client"]
