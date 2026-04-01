import customtkinter as ctk


class UpdateNewsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1) 基本窗口设置
        self.title("UpdateNews")
        self.geometry("980x640")
        self.minsize(900, 600)

        ctk.set_appearance_mode("System")      # "Dark" / "Light" / "System"
        ctk.set_default_color_theme("blue")    # "blue" / "green" / "dark-blue"

        # 2) 全局布局：2列（左侧导航 + 右侧内容）
        self.grid_columnconfigure(0, weight=0)  # 左侧固定宽度
        self.grid_columnconfigure(1, weight=1)  # 右侧自适应
        self.grid_rowconfigure(0, weight=1)

        # 3) 左侧导航栏（占位）
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(99, weight=1)  # 让上面内容靠上

        self.app_title = ctk.CTkLabel(
            self.sidebar,
            text="UpdateNews",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.app_title.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self.nav_home = ctk.CTkButton(self.sidebar, text="主页（占位）")
        self.nav_home.grid(row=1, column=0, padx=16, pady=8, sticky="ew")

        self.nav_urls = ctk.CTkButton(self.sidebar, text="URL 列表（占位）")
        self.nav_urls.grid(row=2, column=0, padx=16, pady=8, sticky="ew")

        self.nav_settings = ctk.CTkButton(self.sidebar, text="设置（占位）")
        self.nav_settings.grid(row=3, column=0, padx=16, pady=8, sticky="ew")

        # 4) 右侧内容区（占位）
        self.content = ctk.CTkFrame(self, corner_radius=12)
        self.content.grid(row=0, column=1, padx=16, pady=16, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        # 5) 初始化页面
        self.current_page = None
        self.show_urls()  # 本块：直接先展示 URL 列表页

    def _set_page(self, page: ctk.CTkFrame):
        if self.current_page is not None:
            self.current_page.destroy()
        self.current_page = page
        self.current_page.grid(row=0, column=0, sticky="nsew")

    def show_home(self):
        page = ctk.CTkFrame(self.content, corner_radius=0)
        page.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(page, text="主页（占位）", font=ctk.CTkFont(size=22, weight="bold"))
        title.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        tip = ctk.CTkLabel(page, text="先做 URL 列表页面，主页稍后再做。")
        tip.grid(row=1, column=0, padx=16, pady=8, sticky="w")

        self._set_page(page)

    def show_settings(self):
        page = ctk.CTkFrame(self.content, corner_radius=0)
        page.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(page, text="设置（占位）", font=ctk.CTkFont(size=22, weight="bold"))
        title.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self._set_page(page)

    # -----------------------
    # 本块重点：URL 列表页面 UI（不联网）
    # -----------------------
    def show_urls(self):
        page = ctk.CTkFrame(self.content, corner_radius=0)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)

        title = ctk.CTkLabel(page, text="URL 列表", font=ctk.CTkFont(size=22, weight="bold"))
        title.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        # 顶部：输入 + 添加
        top = ctk.CTkFrame(page)
        top.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(top, placeholder_text="输入要监控的 URL，例如 https://example.com/rss")
        self.url_entry.grid(row=0, column=0, padx=(12, 8), pady=12, sticky="ew")

        add_btn = ctk.CTkButton(top, text="添加", width=90, command=self._on_add_url)
        add_btn.grid(row=0, column=1, padx=(0, 12), pady=12)

        self.toggle_edit_btn = ctk.CTkButton(top, text="多选", width=90, command=self._toggle_edit_mode)
        self.toggle_edit_btn.grid(row=0, column=2, padx=(0, 12), pady=12)

        # 中间：可滚动列表容器
        self.url_list_frame = ctk.CTkScrollableFrame(page, label_text="已添加的 URL（单选一个作为监控目标）")
        self.url_list_frame.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="nsew")
        self.url_list_frame.grid_columnconfigure(0, weight=1)

        # 底部：状态 + 删除当前
        bottom = ctk.CTkFrame(page)
        bottom.grid(row=3, column=0, padx=16, pady=(0, 16), sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(bottom, text="状态：0 条 URL（未选择监控目标）")
        self.status_label.grid(row=0, column=0, padx=12, pady=12, sticky="w")

        self.del_btn = ctk.CTkButton(
            bottom,
            text="删除当前",
            fg_color="#b33a3a",
            hover_color="#992f2f",
            width=120,
            command=self._on_delete_selected,
        )
        self.del_btn.grid(row=0, column=1, padx=12, pady=12, sticky="e")

        # 数据（内存模拟）
        self.urls = []
        self.active_url_var = ctk.StringVar(value="")  # 单选
        self.edit_mode = ctk.BooleanVar(value=False)  # False=单选监控模式；True=多选编辑模式
        self.select_vars = {}  # 编辑模式下每个URL对应一个BooleanVar（用于多选）
        self.url_rows = []  # 每行保存 {"url": str, "row": frame}

        self._refresh_url_list()
        self._set_page(page)

    def _toggle_edit_mode(self):
        # 切换模式
        self.edit_mode.set(not self.edit_mode.get())

        # 更新按钮文字
        if self.edit_mode.get():
            self.toggle_edit_btn.configure(text="完成")
            self.del_btn.configure(text="删除选中")
        else:
            self.toggle_edit_btn.configure(text="多选")
            self.del_btn.configure(text="删除当前")

        # 刷新列表（会根据 edit_mode 变成 radio/checkbox）
        self._refresh_url_list()

    def _on_add_url(self):
        url = self.url_entry.get().strip()
        if not url:
            return

        if url in self.urls:
            self.url_entry.delete(0, "end")
            return

        self.urls.append(url)
        self.url_entry.delete(0, "end")

        # 若这是第一个URL，自动设为当前监控目标
        if len(self.urls) == 1:
            self.active_url_var.set(url)

        self._refresh_url_list()

    # ✅ 修改1：删除逻辑（满足：编辑模式删除后自动回到单选，并默认运行第一条）
    def _on_delete_selected(self):
        # 编辑模式：删除勾选，多删
        if self.edit_mode.get():
            to_delete = [url for url, var in self.select_vars.items() if var.get()]
            if not to_delete:
                return

            self.urls = [u for u in self.urls if u not in to_delete]

            # 删除后：自动回到单选模式（你要求的行为）
            self.edit_mode.set(False)
            self.toggle_edit_btn.configure(text="多选")
            self.del_btn.configure(text="删除当前")

            # 清空多选勾选状态，避免下次进入编辑模式残留
            self.select_vars.clear()

            # 删除后默认选中第一条，并“运行第一条”
            if self.urls:
                self.active_url_var.set(self.urls[0])
                self._start_monitoring_active()
            else:
                self.active_url_var.set("")

            self._refresh_url_list()
            return

        # 正常模式：删除当前 active（保留功能，不干扰你的编辑模式逻辑）
        active = self.active_url_var.get().strip()
        if not active:
            return

        self.urls = [u for u in self.urls if u != active]

        # 删除后默认选中第一条（与“默认运行第一条”的理念一致）
        if self.urls:
            self.active_url_var.set(self.urls[0])
            self._start_monitoring_active()
        else:
            self.active_url_var.set("")

        self._refresh_url_list()

    def _on_active_changed(self):
        active = self.active_url_var.get().strip()
        if not active:
            self.status_label.configure(text=f"状态：{len(self.urls)} 条 URL（未选择监控目标）")
        else:
            self.status_label.configure(text=f"状态：{len(self.urls)} 条 URL（当前监控：{active}）")

    # ✅ 修改2：状态/刷新逻辑（编辑模式显示提示；单选模式显示 active）
    def _refresh_url_list(self):
        # 清空旧行
        for row in self.url_rows:
            row["row"].destroy()
        self.url_rows.clear()

        # 编辑模式：确保每个 URL 都有一个对应的 BooleanVar
        if hasattr(self, "select_vars"):
            existing = set(self.urls)
            for url in list(self.select_vars.keys()):
                if url not in existing:
                    del self.select_vars[url]

            for url in self.urls:
                if url not in self.select_vars:
                    self.select_vars[url] = ctk.BooleanVar(value=False)

        # 重新渲染
        for i, url in enumerate(self.urls):
            row_frame = ctk.CTkFrame(self.url_list_frame)
            row_frame.grid(row=i, column=0, padx=8, pady=6, sticky="ew")
            row_frame.grid_columnconfigure(1, weight=1)

            if self.edit_mode.get():
                chk = ctk.CTkCheckBox(
                    row_frame,
                    text="",
                    variable=self.select_vars[url],
                    width=24,
                )
                chk.grid(row=0, column=0, padx=(10, 6), pady=10)
            else:
                radio = ctk.CTkRadioButton(
                    row_frame,
                    text="",
                    value=url,
                    variable=self.active_url_var,
                    width=24,
                    command=self._on_active_changed,
                )
                radio.grid(row=0, column=0, padx=(10, 6), pady=10)

            label = ctk.CTkLabel(row_frame, text=url, anchor="w")
            label.grid(row=0, column=1, padx=6, pady=10, sticky="ew")

            self.url_rows.append({"url": url, "row": row_frame})

        # 如果 active_url 已经不在列表里了（比如被删了），清空
        if self.active_url_var.get() not in self.urls:
            self.active_url_var.set("")

        # 状态栏显示：根据当前模式显示不同提示
        if hasattr(self, "status_label"):
            if self.edit_mode.get():
                checked_count = sum(1 for v in self.select_vars.values() if v.get())
                self.status_label.configure(
                    text=f"编辑模式：勾选后删除（已勾选 {checked_count} / 共 {len(self.urls)} 条）"
                )
            else:
                self._on_active_changed()

    def _start_monitoring_active(self):
        active = self.active_url_var.get().strip()
        if not active:
            return
        print("开始监控：", active)


def run_app():
    app = UpdateNewsApp()
    app.mainloop()
