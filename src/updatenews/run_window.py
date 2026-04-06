import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox
from datetime import timezone, timedelta, datetime

from .fetch import default_daily_window, get_matches_in_window
from .formatter import team_short, status_text

TZ_CN = timezone(timedelta(hours=8))


def next_noon_cn(now: datetime) -> datetime:
    """
    给定北京时间 now，返回下一次 12:00（如果现在 < 12:00，返回今天12:00；否则返回明天12:00）
    """
    today_noon = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if now < today_noon:
        return today_noon
    return today_noon + timedelta(days=1)


class RunWindow(tk.Toplevel):
    """
    第二页面：运行窗口
    - 左侧输出台：Text
    - 右侧：停止/继续、抓取、返回主页面、帮助
    - 后台线程定时触发抓取（先用每60秒一次；你后面再改成每天12:00）
    """

    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master

        self.title("瓦罗兰特比赛记录 - 运行中")
        self.geometry("950x520")

        # 状态
        self.running = True   # 窗口存活
        self.paused = False   # 暂停自动输出
        self.q: "queue.Queue[str]" = queue.Queue()

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

        self.btn_back = tk.Button(right, text="返回主页面", command=self.back_to_main)
        self.btn_back.pack(fill=tk.X, padx=10, pady=6)

        self.btn_help = tk.Button(right, text="帮助", command=self.show_help)
        self.btn_help.pack(fill=tk.X, padx=10, pady=6)

        # 关闭确认
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # 开始轮询队列，把输出刷到 Text
        self.after(100, self.drain_queue)

        # 启动后台自动循环
        self.start_auto_loop()
        self.fetch_once_async()

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

    def fetch_once_async(self):
        # 防止疯狂连点：把按钮暂时禁用
        self.btn_fetch.config(state="disabled")

        def job():
            now_cn = datetime.now(TZ_CN)
            try:
                start, end = default_daily_window()
                self.log(f"开始抓取：窗口 {start:%Y-%m-%d %H:%M} ~ {end:%Y-%m-%d %H:%M}, 抓取时间 {now_cn:%Y-%m-%d %H:%M}")
                matches = get_matches_in_window(start, end)
                if not matches:
                    self.log("本时间窗内没有比赛。")
                    return
                for m in matches:
                    self.log(self.format_match_line(m))
            except Exception as e:
                self.log(f"抓取失败：{e}")
            finally:
                # 回到主线程恢复按钮：用 after
                self.after(0, lambda: self.btn_fetch.config(state="normal"))

        threading.Thread(target=job, daemon=True).start()

    # ---------------- 自动循环：先每60秒一次（后续可换每天12点） ----------------
    def start_auto_loop(self):
        def loop():
            # 启动时先输出“下一次触发时间”
            while self.running:
                now_cn = datetime.now(TZ_CN)
                nxt = next_noon_cn(now_cn)
                wait_seconds = (nxt - now_cn).total_seconds()

                self.log(f"下一次自动抓取时间：{nxt:%Y-%m-%d %H:%M}（北京时间）")

                # 等待到点：期间允许暂停/继续
                while self.running:
                    if self.paused:
                        # 暂停时每秒醒一次看看是否恢复/是否关闭
                        time.sleep(1)
                        continue

                    # 未暂停：睡到下一次触发点
                    ok = self.sleep_interruptible(wait_seconds)
                    if not ok:
                        return  # 窗口关闭

                    # 睡醒后再校准一次时间：防止系统休眠/时间漂移
                    now_cn = datetime.now(TZ_CN)
                    if now_cn >= nxt and not self.paused:
                        self.fetch_once_async()
                    break  # 触发一次后，重新计算下一次 12:00

        threading.Thread(target=loop, daemon=True).start()

    # ---------------- 按钮行为 ----------------
    def toggle_pause(self):
        self.paused = not self.paused
        self.btn_pause.config(text="继续" if self.paused else "停止")
        self.log("已暂停自动输出。" if self.paused else "已恢复自动输出。")

    def back_to_main(self):
        if not messagebox.askyesno("确认", "确定返回主页面？将停止运行窗口。"):
            return
        self.running = False
        self.destroy()
        self.master.deiconify()

    def show_help(self):
        messagebox.showinfo(
            "帮助",
            "停止/继续：暂停或恢复自动抓取循环\n"
            "抓取：立即抓取一次并输出\n"
            "返回主页面：关闭运行窗口并回到主窗口\n"
        )

    def on_close(self):
        if not messagebox.askyesno("确认", "确定退出程序？"):
            return
        self.running = False
        self.master.destroy()
