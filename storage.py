"""Simple JSON-backed storage for seen listings."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable, Set, Dict, List


DATA_DIR = Path("./data")
SEEN_FILE = DATA_DIR / "seen.json"


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_seen() -> Set[str]:
    """Load seen listing IDs (backwards compatible with old array format)."""
    _ensure_dir()
    if not SEEN_FILE.exists():
        return set()
    try:
        with SEEN_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data)
    except Exception:
        return set()


def save_seen(ids: Iterable[str]) -> None:
    """Save seen IDs."""
    _ensure_dir()
    with SEEN_FILE.open("w", encoding="utf-8") as f:
        json.dump(list(ids), f, indent=2)


def filter_new(listings: List[Dict]) -> List[Dict]:
    """Given listing dicts (must include `id`), return only new ones
    and update persisted seen ids.
    """
    seen = load_seen()
    new = [l for l in listings if str(l.get("id")) not in seen]
    if new:
        seen.update(str(l.get("id")) for l in new)
        save_seen(seen)
    return new
