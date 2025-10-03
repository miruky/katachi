"""1関数で完結する設定ダイアログ。"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from ..errors import FormValidationError, PersistenceError
from ..persistence import load, save
from . import motion as motion_mod
from . import theme as theme_mod
from .form import Form, ThemeOption
from .scroll import ScrollableFrame


def edit[T](
    model: type[T] | T,
    *,
    store: str | Path | None = None,
    title: str | None = None,
    parent: tk.Misc | None = None,
    theme: ThemeOption = "auto",
    accent: str | None = None,
    motion: bool | None = None,
) -> T | None:
    """設定ダイアログを開く。保存で確定したインスタンス、キャンセルでNoneを返す。

    storeを渡すと初期値をそのファイルから読み、保存時に書き戻す。
    壊れたファイルはデフォルト値として扱い、起動を妨げない。
    themeは "auto"(OS追従・既定)/"light"/"dark"/None(スタイルに触れない)。
    accentに色(`#rrggbb`)を渡すと組み込みのアクセント色を差し替える。
    motionは None で reduced-motion 設定に追従、True/False で明示指定。
    """
    cls: type[T] = model if isinstance(model, type) else type(model)
    if store is not None:
        try:
            initial: T = load(cls, store)
        except PersistenceError:
            initial = cls()
    elif isinstance(model, type):
        initial = cls()
    else:
        initial = model

    owns_root = parent is None
    window: tk.Tk | tk.Toplevel = tk.Tk() if owns_root else tk.Toplevel(parent)
    window.title(title or cls.__name__)
    window.minsize(380, 0)

    # 背の高い設定でも画面に収まるよう、フォームはスクロール領域に入れる。
    # 画面高の7割を上限にし、それを超えた分だけスクロールへ回す。
    max_height = int(window.winfo_screenheight() * 0.7)
    scroll = ScrollableFrame(window, max_height=max_height)
    scroll.pack(fill="both", expand=True)
    form = Form(scroll.interior, initial, theme=theme, accent=accent, motion=motion)
    form.pack(fill="both", expand=True)
    if form.palette is not None:
        scroll.configure_background(form.palette)

    result: list[T | None] = [None]

    def close() -> None:
        motion_mod.fade_out(window, window.destroy, enabled=form.motion)

    def on_save() -> None:
        try:
            value = form.get()
        except FormValidationError:
            form.focus_invalid()
            return
        try:
            if store is not None:
                save(value, store)
        except PersistenceError as error:
            messagebox.showerror("保存できません", str(error), parent=window)
            return
        result[0] = value
        close()

    def on_cancel() -> None:
        close()

    ttk.Separator(window, orient="horizontal").pack(fill="x", padx=theme_mod.SPACE_LG)
    buttons = ttk.Frame(window, padding=(theme_mod.SPACE_LG, theme_mod.SPACE_MD))
    buttons.pack(fill="x")
    ttk.Button(buttons, text="デフォルトに戻す", command=form.reset).pack(side="left")
    ttk.Button(buttons, text="キャンセル", command=on_cancel).pack(side="right")
    ttk.Button(buttons, text="保存", command=on_save, style="Accent.TButton").pack(
        side="right", padx=(0, theme_mod.SPACE_SM)
    )
    window.protocol("WM_DELETE_WINDOW", on_cancel)
    window.bind("<Escape>", lambda _e: on_cancel())
    # 保存のショートカット。Commandはmac、Controlはそれ以外で効く。
    window.bind("<Control-s>", lambda _e: on_save())
    window.bind("<Command-s>", lambda _e: on_save())

    motion_mod.fade_in(window, enabled=form.motion)
    if owns_root:
        window.mainloop()
    else:
        window.grab_set()
        window.wait_window()
    return result[0]
