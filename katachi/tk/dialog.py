"""1関数で完結する設定ダイアログ。"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..errors import FormValidationError, PersistenceError
from ..persistence import load, save
from .form import Form


def edit[T](
    model: type[T] | T,
    *,
    store: str | Path | None = None,
    title: str | None = None,
    parent: tk.Misc | None = None,
) -> T | None:
    """設定ダイアログを開く。保存で確定したインスタンス、キャンセルでNoneを返す。

    storeを渡すと初期値をそのファイルから読み、保存時に書き戻す。
    壊れたファイルはデフォルト値として扱い、起動を妨げない。
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

    form = Form(window, initial)
    form.pack(fill="both", expand=True)

    result: list[T | None] = [None]

    def on_save() -> None:
        try:
            value = form.get()
        except FormValidationError:
            return
        if store is not None:
            save(value, store)
        result[0] = value
        window.destroy()

    def on_cancel() -> None:
        window.destroy()

    buttons = ttk.Frame(window, padding=(12, 0, 12, 12))
    buttons.pack(fill="x")
    ttk.Button(buttons, text="キャンセル", command=on_cancel).pack(side="right")
    ttk.Button(buttons, text="保存", command=on_save).pack(side="right", padx=(0, 8))
    window.protocol("WM_DELETE_WINDOW", on_cancel)
    window.bind("<Escape>", lambda _e: on_cancel())

    if owns_root:
        window.mainloop()
    else:
        window.grab_set()
        window.wait_window()
    return result[0]
