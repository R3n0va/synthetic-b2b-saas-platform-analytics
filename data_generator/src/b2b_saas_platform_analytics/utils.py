from __future__ import annotations

import hashlib
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


def prefixed_id(prefix: str, number: int, width: int = 8) -> str:
    return f"{prefix}_{number:0{width}d}"


def weighted_choice(rng: np.random.Generator, weights: dict[str, float], size: int = 1) -> np.ndarray:
    labels = np.array(list(weights))
    probs = np.array(list(weights.values()), dtype=float)
    probs = probs / probs.sum()
    return rng.choice(labels, size=size, p=probs)


def random_date(
    rng: np.random.Generator,
    start: pd.Timestamp,
    end: pd.Timestamp,
    size: int = 1,
) -> pd.DatetimeIndex:
    if end < start:
        raise ValueError("end must not be earlier than start")
    days = (end.normalize() - start.normalize()).days
    offsets = rng.integers(0, max(days + 1, 1), size=size)
    return pd.to_datetime(start.normalize() + pd.to_timedelta(offsets, unit="D"))


def month_start(value: pd.Timestamp | str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return pd.Timestamp(ts.year, ts.month, 1)


def month_end(value: pd.Timestamp | str) -> pd.Timestamp:
    return month_start(value) + pd.offsets.MonthEnd(0)


def iter_months(start: pd.Timestamp | str, end: pd.Timestamp | str) -> Iterable[pd.Timestamp]:
    return pd.date_range(month_start(start), month_start(end), freq="MS")


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, pd.Period, date, datetime)):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serialisable")


def dataframe_fingerprint(frame: pd.DataFrame) -> str:
    hashed = pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    return hashlib.sha256(hashed).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=json_default), encoding="utf-8", newline="\n")
