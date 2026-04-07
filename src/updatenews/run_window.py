import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox
from datetime import timezone, timedelta, datetime

from .fetch import default_daily_window, get_matches_in_window
from .formatter import team_short, status_text
from .notifier import OneBot11Client, OneBot11Config, format_daily_report, send_report_to_receivers
from .storage import load_onebot_config, load_receivers

TZ_CN = timezone(timedelta(hours=8))


def next_1400_cn(now: datetime) -> datetime:
    today_1400 = now.replace(hour=14, minute=0, second=0, microsecond=0)
    if now < today_1400:
        return today_1400
    return today_1400 + timedelta(days=1)


class RunWindow(tk.Toplevel):
    """
    运行窗口：
    - 自动：每天 14:00 发送“日报”（抓取->格式化->QQ私聊）
    - 默认功能（无需按钮）：启动后抓取一次，把“未开始”比赛加入提醒队列；
      后台线程每 10 秒检查一次，到开赛前 5 分钟给 receivers.json 发送提醒
    """

    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master

        self.title("瓦罗兰特比赛记录 - 运行中")
        self.geometry("950x520")

        # 状态
        self.running = True   # 窗口存活
        self.paused = False   # 暂停“日报自动循环”（不影响提醒，提醒默认一直工作）
        self.q: "queue.Queue[str]" = queue.Queue()

        # 提醒状态（功能1：选项1）
        # reminder_queue: [(remind_at, match_dt, bMatchId, raw_match_dict), ...]
        self.reminder_queue = []
        self.reminded_ids = set()  # 已提醒过的 bMatchId（本次运行内去重）

        # ---- UI 布局 ----
        left = tk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text = tk.Text(left, wrap="word")
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ysb = tk.Scrollbar(left, orient="vertical", command=self.text.yview)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.configure(yscrollcommand=ysb.set)

        right = tk.Frame(self, width=240)
        right.pack(side=tk.RIGHT, fill=tk.Y)

        self.btn_pause = tk.Button(right, text="停止", command=self.toggle_pause)
        self.btn_pause.pack(fill=tk.X, padx=10, pady=(12, 6))

        self.btn_fetch = tk.Button(right, text="抓取", command=self.fetch_once_async)
        self.btn_fetch.pack(fill=tk.X, padx=10, pady=6)

        self.btn_send = tk.Button(right, text="发送日报", command=self.send_daily_report_async)
        self.btn_send.pack(fill=tk.X, padx=10, pady=6)

        self.btn_back = tk.Button(right, text="返回主页面", command=self.back_to_main)
        self.btn_back.pack(fill=tk.X, padx=10, pady=6)

        self.btn_help = tk.Button(right, text="帮助", command=self.show_help)
        self.btn_help.pack(fill=tk.X, padx=10, pady=6)

        # 关闭确认
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # 开始轮询队列，把输出刷到 Text
        self.after(100, self.drain_queue)

        # 启动提醒后台循环（默认功能，不需要按钮）
        self.start_reminder_loop()

        # 启动后台“日报”的自动循环
        self.start_auto_loop()

        # 启动即抓取一次：既展示数据，也构建提醒队列（选1）
        self.fetch_once_async(build_reminders=True)

        self.log("运行窗口已启动。点击“抓取”可立即获取一次。")

    def sleep_interruptible(self, seconds: float) -> bool:
        """
        以 0.5s 步进睡眠，期间如果窗口关闭返回 False
        返回 True 表示睡满了
        """
        end = time.time() + seconds
        while self.running and time.time() < end:
            time.sleep(0.5)
        return self.running

    # ---------------- 输出相关 ----------------
    def log(self, msg: str) -> None:
        self.q.put(msg)

    def drain_queue(self):
        try:
            while True:
                msg = self.q.get_nowait()
                self.text.insert(tk.END, msg + "\n")
                self.text.see(tk.END)
        except queue.Empty:
            pass

        if self.running:
            self.after(100, self.drain_queue)

    # ---------------- 业务：抓取并输出 ----------------
    def format_match_line(self, m: dict) -> str:
        dt = m.get("_parsed_dt")
        time_part = dt.strftime("%m-%d %H:%M") if dt else "未知时间"

        title = m.get("bMatchName", "")
        group = m.get("groupName", "")
        extra = f" | {group}" if group else ""

        a = team_short(m.get("teamA"), "TBD_A")
        b = team_short(m.get("teamB"), "TBD_B")
        score_a = m.get("scoreA", 0)
        score_b = m.get("scoreB", 0)

        st = status_text(m.get("matchStatusId"))
        bmatch_id = m.get("bMatchId", "")

        return f"{time_part}{extra} | {title} | {a} {score_a}:{score_b} {b} | {st} | bMatchId={bmatch_id}"

    def fetch_once_async(self, build_reminders: bool = False):
        """
        抓取一次并输出。
        build_reminders=True 时：用抓取结果更新提醒队列（选1：只在启动时那次抓取用 True）
        """
        # 防止疯狂连点：把按钮暂时禁用
        self.btn_fetch.config(state="disabled")

        def job():
            now_cn = datetime.now(TZ_CN)
            try:
                start, end = default_daily_window()
                self.log(
                    f"开始抓取：窗口 {start:%Y-%m-%d %H:%M} ~ {end:%Y-%m-%d %H:%M}, 抓取时间 {now_cn:%Y-%m-%d %H:%M}"
                )
                matches = get_matches_in_window(start, end)
                if not matches:
                    self.log("本时间窗内没有比赛。")
                    return

                for m in matches:
                    self.log(self.format_match_line(m))

                if build_reminders:
                    self.update_reminder_queue(matches)

            except Exception as e:
                self.log(f"抓取失败：{e!r}")
            finally:
                # 回到主线程恢复按钮：用 after
                self.after(0, lambda: self.btn_fetch.config(state="normal"))

        threading.Thread(target=job, daemon=True).start()

    def send_daily_report_async(self):
        """按计划书：抓取 -> 生成纯文本 -> 给 receivers.json 里的每个QQ私聊发送。"""

        def job():
            now_cn = datetime.now(TZ_CN)
            try:
                # 1) 抓取
                start, end = default_daily_window()
                self.log(
                    f"开始发送日报：窗口 {start:%Y-%m-%d %H:%M} ~ {end:%Y-%m-%d %H:%M}, 触发时间 {now_cn:%Y-%m-%d %H:%M}"
                )
                matches = get_matches_in_window(start, end)

                # 2) 生成文本
                report = format_daily_report(matches, start, end)

                # 3) 读取接收方
                receivers = load_receivers("receivers.json")
                if not receivers:
                    self.log("receivers.json 为空：没有接收方QQ，跳过发送。")
                    return

                # 4) 读取 OneBot 配置
                base_url, token = load_onebot_config("onebot_config.json")
                if not base_url or not token:
                    self.log("onebot_config.json 未配置完整：请填写 base_url 和 token。")
                    return

                client = OneBot11Client(OneBot11Config(base_url=base_url, token=token))

                # 5) 逐个发送并输出结果
                results = send_report_to_receivers(client, receivers, report)
                ok_count = sum(1 for _, ok, _ in results if ok)
                fail_count = len(results) - ok_count
                self.log(f"发送完成：成功 {ok_count}，失败 {fail_count}")
                for r, ok, msg in results:
                    if ok:
                        self.log(f"  [OK] {r}")
                    else:
                        self.log(f"  [FAIL] {r} -> {msg}")

            except Exception as e:
                self.log(f"发送日报失败：{e!r}")

        threading.Thread(target=job, daemon=True).start()

    # ---------------- 自动循环：每天 14:00 发送日报 ----------------
    def start_auto_loop(self):
        def loop():
            while self.running:
                now_cn = datetime.now(TZ_CN)
                nxt = next_1400_cn(now_cn)
                wait_seconds = (nxt - now_cn).total_seconds()

                self.log(f"下一次自动抓取时间：{nxt:%Y-%m-%d %H:%M}（北京时间）")

                while self.running:
                    if self.paused:
                        time.sleep(1)
                        continue

                    ok = self.sleep_interruptible(wait_seconds)
                    if not ok:
                        return  # 窗口关闭

                    now_cn = datetime.now(TZ_CN)
                    if now_cn >= nxt and not self.paused:
                        # 到点执行：发送日报
                        self.send_daily_report_async()
                    break

        threading.Thread(target=loop, daemon=True).start()

    # ---------------- 按钮行为 ----------------
    def toggle_pause(self):
        self.paused = not self.paused
        self.btn_pause.config(text="继续" if self.paused else "停止")
        self.log("已暂停日报自动循环。" if self.paused else "已恢复日报自动循环。")

    def back_to_main(self):
        if not messagebox.askyesno("确认", "确定返回主页面？将停止运行窗口。"):
            return
        self.running = False
        self.destroy()
        self.master.deiconify()

    def show_help(self):
        messagebox.showinfo(
            "帮助",
            "停止/继续：暂停或恢复“日报”自动循环（提醒功能不受影响）\n"
            "抓取：立即抓取一次并输出\n"
            "发送日报：立即执行一次“抓取→生成文本→私聊发送”\n"
            "默认提醒：程序启动后会将未开始比赛加入队列，并在开赛前5分钟自动提醒\n"
            "返回主页面：关闭运行窗口并回到主窗口\n"
        )

    def on_close(self):
        if not messagebox.askyesno("确认", "确定退出程序？"):
            return
        self.running = False
        self.master.destroy()

    # ---------------- 提醒功能（功能1：选1） ----------------
    def update_reminder_queue(self, matches: list[dict]):
        """
        从抓取到的 matches 中筛出“未开始”的比赛，建立提醒队列。
        选1：只在启动时抓取那一次build_reminders=True时进来。
        """
        q = []
        now = datetime.now(TZ_CN)

        for m in matches:
            # 判定未开始：优先 matchStatusId==1；否则退化用 status_text
            mid = m.get("matchStatusId", 0)
            is_upcoming = False
            try:
                is_upcoming = int(mid) == 1
            except Exception:
                is_upcoming = "未开始" in status_text(mid)

            if not is_upcoming:
                continue

            dt = m.get("_parsed_dt")
            if not isinstance(dt, datetime):
                continue

            # 已经开赛很久的就不入队（防止启动时就立刻补发一堆历史提醒）
            if dt < now - timedelta(minutes=1):
                continue

            bmid = m.get("bMatchId")
            if not bmid:
                continue
            try:
                bmid_int = int(bmid)
            except Exception:
                continue

            remind_at = dt - timedelta(minutes=5)
            q.append((remind_at, dt, bmid_int, m))

        q.sort(key=lambda x: x[0])
        self.reminder_queue = q
        self.log(f"提醒队列已更新：{len(q)} 场未开始比赛（开赛前5分钟提醒）")

        # 可选：打印前几条预览
        for remind_at, match_dt, bmid, m in q[:8]:
            title = m.get("bMatchName", "")
            a = team_short(m.get("teamA"), "TBD_A")
            b = team_short(m.get("teamB"), "TBD_B")
            self.log(f"  预告入队：{match_dt:%m-%d %H:%M} | {title} | {a} vs {b} | remind@{remind_at:%m-%d %H:%M} | bMatchId={bmid}")

    def start_reminder_loop(self):
        def loop():
            while self.running:
                try:
                    now = datetime.now(TZ_CN)

                    # 用快照遍历，避免队列被更新时迭代异常
                    for remind_at, match_dt, bmid, m in list(self.reminder_queue):
                        if bmid in self.reminded_ids:
                            continue
                        if now < remind_at:
                            continue

                        title = m.get("bMatchName", "")
                        a = team_short(m.get("teamA"), "TBD_A")
                        b = team_short(m.get("teamB"), "TBD_B")
                        text = f"【赛程提醒】{match_dt:%m-%d %H:%M} {title} {a} vs {b}（5分钟后开始）"

                        # 读取接收方
                        receivers = load_receivers("receivers.json")
                        if not receivers:
                            self.log("提醒发送跳过：receivers.json 为空（没有接收方QQ）。")
                            # 不标记已提醒，避免之后用户补上接收方仍能提醒
                            continue

                        # 读取 OneBot 配置
                        base_url, token = load_onebot_config("onebot_config.json")
                        if not base_url or not token:
                            self.log("提醒发送跳过：onebot_config.json 未配置完整（base_url/token）。")
                            continue

                        client = OneBot11Client(OneBot11Config(base_url=base_url, token=token))

                        # 逐个发送
                        results = send_report_to_receivers(client, receivers, text)
                        ok_count = sum(1 for _, ok, _ in results if ok)
                        fail_count = len(results) - ok_count

                        self.log(f"提醒已触发：bMatchId={bmid} | 成功 {ok_count} 失败 {fail_count}")
                        for r, ok, msg in results:
                            if ok:
                                self.log(f"  [OK] {r}")
                            else:
                                self.log(f"  [FAIL] {r} -> {msg}")

                        # 发送完成才标记（无论部分失败/部分成功，都避免无限重发刷屏）
                        self.reminded_ids.add(bmid)

                    time.sleep(10)

                except Exception as e:
                    # 防止线程悄悄退出
                    self.log(f"提醒线程异常：{e!r}")
                    time.sleep(3)

        threading.Thread(target=loop, daemon=True).start()
