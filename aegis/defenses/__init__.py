"""Defense registry and the named configurations AEGIS benchmarks."""
from __future__ import annotations

from .base import Defense, DefenseStack
from .output_filter import OutputFilter
from .policy import ToolPolicy
from .sanitizer import InputSanitizer
from .spotlighting import DataMarking

__all__ = ["Defense", "DefenseStack", "InputSanitizer", "DataMarking",
           "ToolPolicy", "OutputFilter", "build_defense", "DEFENSE_CONFIGS"]

# Individual layers plus meaningful combinations, so the benchmark can show both
# each layer's standalone value and how layers cover one another's blind spots.
_LAYERS = {
    "sanitizer": InputSanitizer,
    "datamarking": DataMarking,
    "tool-policy": ToolPolicy,
    "output-filter": OutputFilter,
}

DEFENSE_CONFIGS: dict[str, list[str]] = {
    "none": [],
    "sanitizer": ["sanitizer"],
    "datamarking": ["datamarking"],
    "tool-policy": ["tool-policy"],
    "output-filter": ["output-filter"],
    "sanitizer+tool-policy": ["sanitizer", "tool-policy"],
    "datamarking+tool-policy": ["datamarking", "tool-policy"],
    "full": ["sanitizer", "datamarking", "tool-policy", "output-filter"],
}


def build_defense(name: str) -> DefenseStack:
    if name not in DEFENSE_CONFIGS:
        raise KeyError(f"unknown defense config '{name}'. "
                       f"known: {', '.join(DEFENSE_CONFIGS)}")
    layers = [_LAYERS[l]() for l in DEFENSE_CONFIGS[name]]
    return DefenseStack(layers, name=name)
