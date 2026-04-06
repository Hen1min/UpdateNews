import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import ttk

from .storage import (
    load_onebot_config,
    load_receivers,
    save_onebot_config,
    save_receivers,
)


RECEIVERS_FILE = "receivers.json"
ONEBOT_FILE = "onebot_config.json"
DEFAULT_BASE_URL = "http://127.0.0.1:3000"


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("瓦罗兰特比赛记录")
        self.geometry("720x480")

        # 数据
        self.receivers = load_receivers(RECEIVERS_FILE)

        # OneBot 配置
        base_url, token = load_onebot_config(ONEBOT_FILE)
        self.base_url_var = tk.StringVar(value=base_url or DEFAULT_BASE_URL)
        self.token_var = tk.StringVar(value=token or "")

        # ---- UI: 标题 ----
        title = tk.Label(self, text="瓦罗兰特比赛记录", font=("Microsoft YaHei", 20, "bold"))
        title.pack(pady=(20, 10))

        # ---- UI: OneBot 配置（标题下方）----
        cfg = tk.LabelFrame(self, text="NapCat / OneBot11 配置")
        cfg.pack(fill=tk.X, padx=20, pady=(0, 10))

        row1 = tk.Frame(cfg)
        row1.pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(row1, text="base_url：", width=10, anchor="e").pack(side=tk.LEFT)
        tk.Entry(row1, textvariable=self.base_url_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        row2 = tk.Frame(cfg)
        row2.pack(fill=tk.X, padx=10, pady=4)
        tk.Label(row2, text="token：", width=10, anchor="e").pack(side=tk.LEFT)
        tk.Entry(row2, textvariable=self.token_var, show="*").pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_row = tk.Frame(cfg)
        btn_row.pack(fill=tk.X, padx=10, pady=(4, 8))
        tk.Button(btn_row, text="保存配置", command=self.save_onebot_ui).pack(side=tk.RIGHT)

        # ---- UI: 中间区域（列表 + 按钮）----
        mid = tk.Frame(self)
        mid.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 左：账号列表
        self.manage_mode = False
        self.checked = set()  # 存 receiver 字符串

        tree_wrap = tk.Frame(mid)
        tree_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            tree_wrap,
            columns=("check", "qq"),
            show="headings",
            selectmode="browse",  # 单选即可，多选靠勾选
        )
        self.tree.heading("check", text="")
        self.tree.heading("qq", text="接收方QQ")
        self.tree.column("check", width=40, anchor="center", stretch=False)
        self.tree.column("qq", width=400, anchor="w")

        ysb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)

        # 点击切换勾选
        self.tree.bind("<Button-1>", self.on_tree_click)

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
        self.refresh_tree()

        # 关闭确认
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- 数据/列表 ----------
    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for qq in self.receivers:
            if self.manage_mode:
                mark = "☑" if qq in self.checked else "☐"
            else:
                mark = ""
            # 注意：iid 用 qq 字符串，要求 qq 不能重复（你已经做了去重）
            self.tree.insert("", tk.END, iid=qq, values=(mark, qq))

    def persist(self):
        save_receivers(RECEIVERS_FILE, self.receivers)

    def save_onebot_ui(self):
        base_url = (self.base_url_var.get() or "").strip()
        token = (self.token_var.get() or "").strip()

        if not base_url:
            base_url = DEFAULT_BASE_URL
            self.base_url_var.set(base_url)

        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            messagebox.showwarning("提示", "base_url 需要以 http:// 或 https:// 开头")
            return

        save_onebot_config(ONEBOT_FILE, base_url, token)
        messagebox.showinfo("提示", "OneBot 配置已保存。")

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
        self.refresh_tree()

    def delete_selected(self):
        if self.manage_mode:
            if not self.checked:
                messagebox.showwarning("提示", "请先勾选要删除的账号。")
                return
            if not messagebox.askyesno("确认", f"确定删除勾选的 {len(self.checked)} 个账号吗？"):
                return
            self.receivers = [r for r in self.receivers if r not in self.checked]
            self.checked.clear()
            self.persist()
            self.refresh_tree()
            return

        # 非管理模式：删当前选中行
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选中要删除的账号。")
            return
        qq = sel[0]
        if not messagebox.askyesno("确认", f"确定删除账号：{qq} ？"):
            return
        self.receivers.remove(qq)
        self.persist()
        self.refresh_tree()

    def toggle_manage(self):
        self.manage_mode = not self.manage_mode
        self.btn_manage.config(text="退出管理" if self.manage_mode else "管理")

        if not self.manage_mode:
            # 退出管理时清空勾选（按你设计也可以保留）
            self.checked.clear()

        self.refresh_tree()

    def toggle_select_all(self):
        if not self.manage_mode:
            messagebox.showinfo("提示", "请先点击“管理”进入勾选模式。")
            return

        if len(self.checked) == len(self.receivers):
            self.checked.clear()
        else:
            self.checked = set(self.receivers)

        self.refresh_tree()

    def start_run(self):
        from .run_window import RunWindow
        self.withdraw()          # 隐藏主窗口
        RunWindow(self)          # 打开运行窗口


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

    def on_tree_click(self, event):
        # identify column/row
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        col = self.tree.identify_column(event.x)  # '#1' 是第一列
        row = self.tree.identify_row(event.y)     # iid

        if not row:
            return

        # 非管理模式：允许正常选择行
        if not self.manage_mode:
            return

        # 管理模式：只在第一列点击才切换勾选
        if col in ("#1", "#2"):  # 你可以选择只在 "#1" 列（勾选列）切换，或者两列都切换
            qq = row
            if qq in self.checked:
                self.checked.remove(qq)
            else:
                self.checked.add(qq)

            # 只更新这一行显示也行；简单起见直接刷新
            self.refresh_tree()
            self.tree.selection_set(row)  # 切换勾选后顺便选中行，方便用户知道哪个被操作了


