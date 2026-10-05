"""Analytic benchmark simulator described by the project knowledge base."""

from .config import PhysicsConfig
from .judgment import generate_judgment_pair
from .sampler import sample_scene
from .simulator import simulate_scene

__all__ = [
    "PhysicsConfig",
    "generate_judgment_pair",
    "sample_scene",
    "simulate_scene",
]

__version__ = "0.1.0"
