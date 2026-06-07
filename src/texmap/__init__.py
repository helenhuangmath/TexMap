"""TexMap: a universal coordinate system for T-cell exhaustion.

Reference atlas, projection, regulatory-network recovery, clinical-translation
benchmarking, an interactive web explorer, and a programmatic TexAPI.
"""

from texmap.config import TexMapConfig, load_config
from texmap.texapi import TexAPIClient, TexMap

__all__ = ["TexMapConfig", "load_config", "TexMap", "TexAPIClient"]
__version__ = "0.2.0"
