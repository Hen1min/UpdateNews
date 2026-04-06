import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

DEFAULT_URL = "https://val.native.game.qq.com/esports/v1/data/VAL_Match_1000060.json"
TZ_CN = timezone(timedelta(hours=8))

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

def get_matches_in_window(
    start: datetime,
    end: datetime,
    url: str = DEFAULT_URL
) -> List[Dict[str, Any]]:
    """
    返回在 [start, end) 时间窗内的比赛 dict 列表（按时间升序排序）
    """
    data = fetch_json(url)
    matches = data.get("msg")
    if not isinstance(matches, list):
        raise ValueError(f"Unexpected JSON shape: msg is not list. keys={list(data.keys())}")

    rows: List[Dict[str, Any]] = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        dt = parse_match_datetime(m.get("matchDate", ""))
        if not dt:
            continue
        if not (start <= dt < end):
            continue
        m["_parsed_dt"] = dt
        rows.append(m)

    rows.sort(key=lambda x: x["_parsed_dt"])
    return rows


def default_daily_window(now: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """
    你计划书的窗口：昨日12:00 ~ 今日24:00（北京时间）
    """
    now_cn = now.astimezone(TZ_CN) if now else datetime.now(TZ_CN)
    today_12 = now_cn.replace(hour=12, minute=0, second=0, microsecond=0)
    end = today_12 + timedelta(hours=12)
    start = today_12 - timedelta(days=1)

    return start, end