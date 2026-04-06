from datetime import datetime
from typing import Any, Dict, List, Optional

def status_text(match_status_id: Any) -> str:
    """
    你接口里给的是数值 matchStatusId，但没给枚举表。
    这里先做一个“尽量不胡说”的输出：未知就打印原值。
    常见约定：1 未开始，2 进行中，3 已结束（不保证，仅作显示友好）
    """
    mapping = {
        1: "未开始",
        2: "进行中",
        3: "已结束",
    }
    try:
        mid = int(match_status_id)
    except Exception:
        return f"状态={match_status_id}"
    return mapping.get(mid, f"状态={mid}")


def team_short(team: Optional[Dict[str, Any]], fallback: str) -> str:
    """
    你样例里 teamA/teamB 包含:
    teamSpName: "BLG"
    teamShortName: "BLG"
    """
    if not isinstance(team, dict):
        return fallback
    return (team.get("teamSpName")
            or team.get("teamShortName")
            or team.get("teamName")
            or fallback)