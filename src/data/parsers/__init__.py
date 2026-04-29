"""CAE tool parsers.

Each parser reads tool-native output files and produces UnifiedCAERecords.
All parsers inherit from BaseParser and must implement the abstract interface.
"""

from src.data.parsers.base import BaseParser

__all__ = ["BaseParser"]
