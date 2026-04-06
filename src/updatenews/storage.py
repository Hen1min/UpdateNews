import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def project_root() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后的 exe 所在目录
        return Path(sys.executable).resolve().parent
    # 开发环境：UpdateNews/src/updatenews/storage.py -> UpdateNews/
    return Path(__file__).resolve().parents[2]



def resolve_in_project_root(path: str) -> Path:
    """Resolve a relative path in the project root."""

    p = Path(path)
    if p.is_absolute():
        return p
    return project_root() / p


def load_receivers(path: str) -> List[str]:
    p = resolve_in_project_root(path)
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
    p = resolve_in_project_root(path)
    p.write_text(json.dumps(receivers, ensure_ascii=False, indent=2), encoding="utf-8")


def load_onebot_config(path: str) -> Tuple[str, str]:
    """Load OneBot11 HTTP config from JSON.

    Expected shape:
    {
      "base_url": "http://127.0.0.1:3000",
      "token": "..."
    }
    """

    p = resolve_in_project_root(path)
    if not p.exists():
        return "", ""
    try:
        data: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return "", ""

    if not isinstance(data, dict):
        return "", ""
    base_url = data.get("base_url")
    token = data.get("token")
    return (
        str(base_url).strip() if isinstance(base_url, str) else "",
        str(token).strip() if isinstance(token, str) else "",
    )


def save_onebot_config(path: str, base_url: str, token: str) -> None:
    p = resolve_in_project_root(path)
    payload = {
        "base_url": base_url.strip(),
        "token": token.strip(),
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

