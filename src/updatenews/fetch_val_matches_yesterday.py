import json
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests


# ==== 1) 你的代理（你已经验证能用） ====
PROXIES = {
    "http": "http://127.0.0.1:9674",
    "https": "http://127.0.0.1:9674",
}

# ==== 2) 这个接口是 persisted query，需要 sha256Hash（你抓包里有） ====
SHA256_HASH = "7246add6f577cf30b304e651bf9e25fc6a41fe49aeafb0754c16b5778060fc0a"
OP_NAME = "homeEvents"

BASE_URL = "https://valorantesports.com/api/gql"

HEADERS = {
    "accept": "application/graphql-response+json,application/json;q=0.9",
    "apollographql-client-name": "Esports Web",
    "user-agent": "Mozilla/5.0",
}


def iso_z(dt: datetime) -> str:
    """把 datetime 转成像 2026-04-01T00:00:00.000Z 这种格式"""
    # dt 必须是 UTC 时区
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def build_url_for_yesterday_cn(page_size: int = 300) -> str:
    """
    目标：抓“北京时间昨天 00:00~23:59:59”的比赛。
    网站接口用的是 UTC 时间范围，所以要把北京时间范围换算成 UTC。
    """
    tz_cn = timezone(timedelta(hours=8))

    # 今天（北京时间）00:00
    now_cn = datetime.now(tz=tz_cn)
    today_00_cn = now_cn.replace(hour=0, minute=0, second=0, microsecond=0)

    # 昨天（北京时间）00:00 ~ 昨天 23:59:59.999
    y_start_cn = today_00_cn - timedelta(days=1)
    y_end_cn = today_00_cn - timedelta(milliseconds=1)

    # 转成 UTC 给接口
    y_start_utc = y_start_cn.astimezone(timezone.utc)
    y_end_utc = y_end_cn.astimezone(timezone.utc)

    variables = {
        "hl": "en-US",
        "sport": "val",
        "eventDateStart": iso_z(y_start_utc),
        "eventDateEnd": iso_z(y_end_utc),
        "eventState": ["inProgress", "completed", "unstarted"],
        "eventType": "all",      # ✅ 全赛区综合
        "vodType": ["recap"],
        "pageSize": page_size,
    }

    # extensions：persistedQuery
    extensions = {
        "clientLibrary": {"name": "@apollo/client", "version": "4.1.2"},
        "persistedQuery": {"version": 1, "sha256Hash": SHA256_HASH},
    }

    # URL 需要把 json 串进行 url-encode
    variables_q = quote(json.dumps(variables, separators=(",", ":")))
    extensions_q = quote(json.dumps(extensions, separators=(",", ":")))

    return f"{BASE_URL}?operationName={OP_NAME}&variables={variables_q}&extensions={extensions_q}"


def extract_match_lines(payload: dict) -> list[str]:
    """
    从 GraphQL 返回 JSON 提取比赛行：
    Team A 2:1 Team B
    """
    data = payload.get("data") or {}
    home = data.get("homeEvents") or {}

    # ⚠️ homeEvents 下的字段名我无法 100% 保证（不同版本可能叫 events/items/sections）
    # 所以我们做一个“兼容式查找”：把可能的列表字段都试一遍。
    candidates = []
    for key in ("events", "items", "matches", "cards"):
        v = home.get(key)
        if isinstance(v, list):
            candidates = v
            break

    # 如果这里 candidates 还是空，说明 events 的路径不是这些名字
    # 你把 homeEvents keys 输出给我，我就能把路径改准。
    if not candidates:
        raise KeyError(f"找不到 events 列表。homeEvents keys = {list(home.keys())}")

    lines = []
    for ev in candidates:
        if not isinstance(ev, dict):
            continue

        if ev.get("type") != "match":
            continue
        if ev.get("state") != "completed":
            continue

        teams = ev.get("matchTeams") or []
        if len(teams) != 2:
            continue

        a, b = teams[0], teams[1]
        a_name = a.get("name", "").strip()
        b_name = b.get("name", "").strip()
        a_wins = ((a.get("result") or {}).get("gameWins"))
        b_wins = ((b.get("result") or {}).get("gameWins"))

        if not a_name or not b_name:
            continue
        if not isinstance(a_wins, int) or not isinstance(b_wins, int):
            continue

        lines.append(f"{a_name} {a_wins}:{b_wins} {b_name}")

    return lines


def main():
    url = build_url_for_yesterday_cn()
    r = requests.get(url, proxies=PROXIES, headers=HEADERS, timeout=30)
    print("HTTP:", r.status_code, "len:", len(r.text))
    r.raise_for_status()

    payload = r.json()

    # 如果接口返回 errors，这里直接打印出来（方便排错）
    if payload.get("errors"):
        print("GraphQL errors:", payload["errors"])
        return

    try:
        lines = extract_match_lines(payload)
    except Exception as e:
        # 失败时把 homeEvents keys 打印出来，你贴给我我就能立刻修正路径
        data = payload.get("data") or {}
        home = (data.get("homeEvents") or {})
        print("解析失败：", repr(e))
        print("homeEvents keys:", list(home.keys()))
        return

    if not lines:
        print("昨天没有抓到 completed matches（可能昨天没比赛，或 events 路径不对）")
        return

    # 输出
    print("\n".join(lines))


if __name__ == "__main__":
    main()
