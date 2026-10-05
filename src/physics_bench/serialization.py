"""Strict JSON conversion helpers for benchmark records."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def to_builtin(value: Any) -> Any:
    """Convert records to JSON-safe builtins while rejecting NaN and infinity."""
    if is_dataclass(value):
        return {field.name: to_builtin(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, np.ndarray):
        return to_builtin(value.tolist())
    if isinstance(value, np.generic):
        return to_builtin(value.item())
    if isinstance(value, dict):
        return {str(key): to_builtin(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_builtin(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("schema serialization forbids NaN and infinity")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported serialization type: {type(value)!r}")


def dumps_json(value: Any, *, indent: int | None = None) -> str:
    return json.dumps(
        to_builtin(value),
        ensure_ascii=False,
        allow_nan=False,
        indent=indent,
        sort_keys=True,
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_json(value, indent=2) + "\n", encoding="utf-8")
