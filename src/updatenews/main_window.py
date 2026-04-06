import tkinter as tk
from tkinter import messagebox, simpledialog

from .storage import load_receivers, save_receivers


RECEIVERS_FILE = "receivers.json"


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("瓦罗兰特比赛记录")
        self.geometry("720x480")

        # 数据
        self.receivers = load_receivers(RECEIVERS_FILE)

        # ---- UI: 标题 ----
        title = tk.Label(self, text="瓦罗兰特比赛记录", font=("Microsoft YaHei", 20, "bold"))
        title.pack(pady=(20, 10))

        # ---- UI: 中间区域（列表 + 按钮）----
        mid = tk.Frame(self)
        mid.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 左：账号列表
        self.listbox = tk.Listbox(mid, selectmode=tk.EXTENDED)  # 支持多选
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 右：操作按钮
        op = tk.Frame(mid, width=200)
        op.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))

        tk.Button(op, text="增加", command=self.add_receiver).pack(fill=tk.X, pady=(0, 8))
        tk.Button(op, text="删除", command=self.delete_selected).pack(fill=tk.X, pady=8)

        self.manage_mode = False
        self.btn_manage = tk.Button(op, text="管理", command=self.toggle_manage)
        self.btn_manage.pack(fill=tk.X, pady=8)

        self.btn_select_all = tk.Button(op, text="全选", command=self.toggle_select_all)
        self.btn_select_all.pack(fill=tk.X, pady=8)

        # ---- UI: 底部区域（开始运行 + 帮助）----
        bottom = tk.Frame(self)
        bottom.pack(fill=tk.X, padx=20, pady=(10, 20))

        tk.Button(bottom, text="开始运行", height=2, command=self.start_run).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10)
        )
        tk.Button(bottom, text="帮助", height=2, command=self.show_help).pack(side=tk.RIGHT)

        # 初始化列表
        self.refresh_listbox()

        # 关闭确认
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- 数据/列表 ----------
    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for r in self.receivers:
            self.listbox.insert(tk.END, r)

    def persist(self):
        save_receivers(RECEIVERS_FILE, self.receivers)

    # ---------- 按钮行为 ----------
    def add_receiver(self):
        qq = simpledialog.askstring("增加账号", "请输入接收方QQ号：", parent=self)
        if not qq:
            return
        qq = qq.strip()
        if not qq:
            return
        if qq in self.receivers:
            messagebox.showwarning("提示", "该账号已存在。")
            return
        self.receivers.append(qq)
        self.persist()
        self.refresh_listbox()

    def delete_selected(self):
        sel = list(self.listbox.curselection())
        if not sel:
            messagebox.showwarning("提示", "请先选中要删除的账号。")
            return
        if not messagebox.askyesno("确认", f"确定删除选中的 {len(sel)} 个账号吗？"):
            return
        for idx in reversed(sel):
            del self.receivers[idx]
        self.persist()
        self.refresh_listbox()

    def toggle_manage(self):
        # 先做“逻辑上的管理模式”（你 UI 的勾选框后面再升级）
        self.manage_mode = not self.manage_mode
        self.btn_manage.config(text="退出管理" if self.manage_mode else "管理")

    def toggle_select_all(self):
        n = self.listbox.size()
        if n == 0:
            return
        if len(self.listbox.curselection()) == n:
            self.listbox.selection_clear(0, tk.END)
        else:
            self.listbox.selection_set(0, tk.END)

    def start_run(self):
        # 第二页面后面再接：这里先留接口，避免你流程断掉
        messagebox.showinfo("提示", "运行窗口（第二页面）还未实现。先把主页面做完整。")

    def show_help(self):
        messagebox.showinfo(
            "帮助",
            "主页面功能：\n"
            "- 增加/删除接收方QQ账号\n"
            "- 管理：进入多选模式（当前用 Listbox 多选模拟）\n"
            "- 全选：选中/取消选中所有账号\n"
            "- 开始运行：后续进入运行窗口\n"
        )

    def on_close(self):
        if messagebox.askyesno("确认", "确定退出程序？"):
            self.destroy()
