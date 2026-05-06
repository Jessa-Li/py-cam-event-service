"""Stub ML classifier.

In production this would be a separate worker process consuming motion events
from a queue and writing alerts back (see "Cloud roadmap" in README.md). For
the MVP we run it inline at ingest time so the demo is end-to-end without a
queue layer — same Alert table, same downstream contract, only the dispatch
mechanism changes.
"""
import os
import random
from typing import Optional, TypedDict


class Classification(TypedDict):
    label: str
    score: float


# Below this score we don't fire an alert. Configurable so tests can force
# (or suppress) alerting without monkeypatching.
THRESHOLD = float(os.environ.get("ML_THRESHOLD", "0.7"))


def classify(payload: Optional[dict], confidence: float) -> Optional[Classification]:
    """Return {'label', 'score'} when score >= THRESHOLD, else None.

    The real classifier would look at the video frame referenced by the
    event's video_url. This stub noises the camera-side confidence and picks
    a label by zone — enough to demo the alert pipeline end-to-end.
    """
    score = min(1.0, max(0.0, confidence + random.uniform(-0.1, 0.05)))
    if score < THRESHOLD:
        return None

    zone = (payload or {}).get("zone", "") if isinstance(payload, dict) else ""
    label_pool = {
        "porch": ["package", "person", "vehicle"],
        "driveway": ["vehicle", "person"],
        "yard": ["person", "animal"],
    }.get(zone, ["person", "vehicle", "package", "animal"])

    return {"label": random.choice(label_pool), "score": round(score, 3)}
