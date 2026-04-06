from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import requests

from .formatter import status_text, team_short


JsonDict = Dict[str, Any]


class OneBot11Error(RuntimeError):
    """OneBot11/NapCat 调用失败时抛出的异常。"""


@dataclass(frozen=True)
class OneBot11Config:
    base_url: str = "http://127.0.0.1:3000"
    token: str = ""  # access_token


class OneBot11Client:
    """
    NapCat OneBot11 HTTP 客户端（你现在验证可用的模式）。
    - base_url 例: http://127.0.0.1:3000
    - token 通过 Authorization: Bearer 传递（你已测通）
    """

    def __init__(self, config: OneBot11Config):
        self.base_url = config.base_url.rstrip("/")
        self.token = config.token.strip()

    def call_api(self, action: str, params: JsonDict) -> JsonDict:
        url = f"{self.base_url}/{action}"
        headers: Dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        r = requests.post(url, json=params, headers=headers, timeout=20)

        # NapCat 有时会返回 403 并在 body 给出原因（如 token verify failed）
        if r.status_code != 200:
            raise OneBot11Error(f"HTTP {r.status_code} for {url}: {r.text}")

        try:
            data = r.json()
        except Exception as e:
            raise OneBot11Error(f"Invalid JSON response for {url}: {r.text}") from e

        # OneBot11 语义错误（retcode != 0）
        # 你之前见过 retcode=200 "无法获取用户信息"
        if isinstance(data, dict):
            retcode = data.get("retcode")
            status = data.get("status")
            if (status == "failed") or (isinstance(retcode, int) and retcode != 0):
                raise OneBot11Error(
                    f"OneBot failed: action={action}, retcode={retcode}, "
                    f"message={data.get('message')}, wording={data.get('wording')}"
                )
        return data

    def get_status(self) -> JsonDict:
        return self.call_api("get_status", {})

    def get_login_info(self) -> JsonDict:
        return self.call_api("get_login_info", {})

    def send_private_text(self, user_id: Union[int, str], text: str) -> JsonDict:
        uid = int(user_id)
        return self.call_api("send_private_msg", {"user_id": uid, "message": text})


# ----------------------------
# 格式化：matches -> 纯文本
# ----------------------------

def _time_mmdd_hhmm(dt: datetime) -> str:
    return dt.strftime("%m-%d %H:%M")


def _is_upcoming(match: JsonDict) -> bool:
    """
    判断是否“预告/未开始”。
    你当前 mapping 约定：matchStatusId=1 未开始。
    同时兼容 status_text 输出包含“未开始”的情况。
    """
    mid = match.get("matchStatusId")
    try:
        mid_int = int(mid)
    except Exception:
        mid_int = None

    if mid_int == 1:
        return True

    st = status_text(mid)
    return "未开始" in st


def _format_one_match_line(match: JsonDict) -> Optional[str]:
    """
    输出类似你示例的单行：
    04-05 19:00 | 常规赛 第一周 | BLG 2:0 JDG | 已结束
    未开始则输出：
    04-06 15:00 | 常规赛 第二周 | BLG vs JDG | 未开始
    """
    dt = match.get("_parsed_dt")
    if not isinstance(dt, datetime):
        return None

    title = match.get("bMatchName") or "未知赛事"
    a = team_short(match.get("teamA"), "TBD_A")
    b = team_short(match.get("teamB"), "TBD_B")
    st = status_text(match.get("matchStatusId"))

    if _is_upcoming(match):
        return f"{_time_mmdd_hhmm(dt)} | {title} | {a} vs {b} | {st}"

    score_a = match.get("scoreA", "")
    score_b = match.get("scoreB", "")
    return f"{_time_mmdd_hhmm(dt)} | {title} | {a} {score_a}:{score_b} {b} | {st}"


def format_daily_report(
    matches: List[JsonDict],
    start: datetime,
    end: datetime,
    title: str = "【VALORANT 比分播报】",
) -> str:
    """
    把 fetch.get_matches_in_window() 返回的 matches 格式化成 QQ 私聊纯文本。
    约定：fetch.py 会给每条 match 填充 `_parsed_dt` 供排序/展示。
    """
    lines: List[str] = []
    lines.append(title)
    lines.append(f"时间窗：{start:%m-%d %H:%M} ~ {end:%m-%d %H:%M}")
    lines.append("")

    finished: List[str] = []
    upcoming: List[str] = []

    for m in matches:
        line = _format_one_match_line(m)
        if not line:
            continue
        if _is_upcoming(m):
            upcoming.append(line)
        else:
            finished.append(line)

    # 你原 matches 已在 fetch.get_matches_in_window 排序过；这里保持顺序即可
    if finished:
        lines.append("已结束/进行中：")
        lines.extend(finished)
        lines.append("")

    if upcoming:
        lines.append("今日预告：")
        lines.extend(upcoming)
        lines.append("")

    if not finished and not upcoming:
        lines.append("本时段内暂无比赛数据。")

    # 防止最后多一个空行也无所谓，但这里稍微收一下
    text = "\n".join(lines).rstrip()
    return text


# ----------------------------
# 多接收方发送（对齐 receivers.json）
# ----------------------------

def send_report_to_receivers(
    client: OneBot11Client,
    receivers: Iterable[Union[str, int]],
    report_text: str,
) -> List[Tuple[Union[str, int], bool, str]]:
    """
    给多个接收方逐个发送。
    返回每个接收方的发送结果，方便 UI 展示/日志记录：
    [(receiver, ok, message), ...]
    """
    results: List[Tuple[Union[str, int], bool, str]] = []
    for r in receivers:
        try:
            client.send_private_text(r, report_text)
            results.append((r, True, "ok"))
        except Exception as e:
            results.append((r, False, str(e)))
    return results
