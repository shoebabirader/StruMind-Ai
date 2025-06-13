"""
Foundation design module
"""

from .shallow_foundation import ShallowFoundationDesign
from .deep_foundation import DeepFoundationDesign
from .foundation_design import FoundationDesign

__all__ = [
    "ShallowFoundationDesign",
    "DeepFoundationDesign", 
    "FoundationDesign"
]