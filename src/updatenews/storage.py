import json
from pathlib import Path
from typing import List


def load_receivers(path: str) -> List[str]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    # 仅保留字符串
    return [x for x in data if isinstance(x, str) and x.strip()]


def save_receivers(path: str, receivers: List[str]) -> None:
    p = Path(path)
    p.write_text(json.dumps(receivers, ensure_ascii=False, indent=2), encoding="utf-8")
