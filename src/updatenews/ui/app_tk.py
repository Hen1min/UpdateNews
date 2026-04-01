import customtkinter as ctk


def run_app():
    ctk.set_appearance_mode("System")      # Dark / Light / System
    ctk.set_default_color_theme("blue")    # blue / green / dark-blue

    app = ctk.CTk()
    app.title("UpdateNews")
    app.geometry("900x600")

    title = ctk.CTkLabel(app, text="UpdateNews - 主界面（占位）", font=ctk.CTkFont(size=20, weight="bold"))
    title.pack(padx=20, pady=20, anchor="w")

    app.mainloop()
