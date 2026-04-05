import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

URL = "https://val.native.game.qq.com/esports/v1/data/VAL_Match_1000060.json"


def fetch_json(url: str) -> Dict[str, Any]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://val.qq.com/",
    }
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return json.loads(r.text)


def parse_match_datetime(match_date: str) -> Optional[datetime]:
    """
    输入示例: "2026-04-15T19:00:00+08:00"
    Python3.13: datetime.fromisoformat 支持该格式
    """
    if not match_date:
        return None
    try:
        return datetime.fromisoformat(match_date)
    except ValueError:
        return None


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


def main():
    data = fetch_json(URL)

    matches = data.get("msg")
    if not isinstance(matches, list):
        print("返回数据结构不符合预期：msg 不是 list")
        print("top keys:", list(data.keys()))
        return

    TZ_CN = timezone(timedelta(hours=8))

    # “今天12:00”（按本机当前日期，固定北京时间）
    now_cn = datetime.now(TZ_CN)
    today_12 = now_cn.replace(hour=12, minute=0, second=0, microsecond=0)

    # 如果现在还没到12点，那么“今天12点”其实是未来；按你的业务一般是到点触发
    # 但为了手动运行也合理：若当前<12点，就用“昨天12点~今天12点(当前日期)”这个窗口
    end = today_12
    start = end - timedelta(days=1)

    parsed_rows: List[Tuple[datetime, str]] = []

    for m in matches:
        if not isinstance(m, dict):
            continue

        # 基本字段
        bmatch_id = m.get("bMatchId", "")
        title = m.get("bMatchName", "")  # 如：常规赛 第三周 / 排位赛Day1
        group = m.get("groupName", "")
        when_raw = m.get("matchDate", "")
        dt = parse_match_datetime(when_raw)

        if not dt:
            continue  # 没有时间的记录先不处理

        # 只保留 [start, end) 这个时间窗内的比赛
        if not (start <= dt < end):
            continue

        # 队伍信息（有些记录 teamA/teamB 可能不存在）
        a = team_short(m.get("teamA"), fallback="TBD_A")
        b = team_short(m.get("teamB"), fallback="TBD_B")

        score_a = m.get("scoreA", "")
        score_b = m.get("scoreB", "")

        st = status_text(m.get("matchStatusId"))

        # 格式化时间：输出 04-15 19:00
        if dt:
            time_part = dt.strftime("%m-%d %H:%M")
        else:
            time_part = str(when_raw) if when_raw else "未知时间"

        # 组合显示文本
        extra = ""
        if group:
            extra = f" | {group}"

        line = f"{time_part}{extra} | {title} | {a} {score_a}:{score_b} {b} | {st} | bMatchId={bmatch_id}"

        # 有 dt 才参与排序，否则放最后
        if dt:
            parsed_rows.append((dt, line))
        else:
            parsed_rows.append((datetime.max, line))

    parsed_rows.sort(key=lambda x: x[0])

    for _, line in parsed_rows:
        print(line)


if __name__ == "__main__":
    main()
