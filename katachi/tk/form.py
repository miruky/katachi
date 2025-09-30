"""FieldSpecの木からttkウィジェットのフォームを組み立てる。"""

from __future__ import annotations

import dataclasses
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, ttk
from typing import Any, Literal

from ..errors import FieldError, FormValidationError
from ..schema import FieldSpec, introspect
from ..validation import coerce_field, display_choice
from . import motion as motion_mod
from . import theme as theme_mod

ThemeOption = Literal["auto", "light", "dark"] | None


class Form(ttk.Frame):
    """dataclassの型またはインスタンスからフォームを生成するウィジェット。

    getで現在の入力を検証つきで取り出し、setでインスタンスを流し込む。
    themeは "auto"(OS追従・既定)/"light"/"dark"/None(スタイルに触れない)。
    motionは None で reduced-motion 設定に追従、True/False で明示指定。
    """

    def __init__(
        self,
        master: tk.Misc,
        model: type | Any,
        *,
        on_change: Callable[[], None] | None = None,
        theme: ThemeOption = "auto",
        motion: bool | None = None,
    ) -> None:
        super().__init__(master, padding=theme_mod.SPACE_LG)
        cls = model if isinstance(model, type) else type(model)
        # 先にイントロスペクトしておくと、必須フィールド(デフォルト無し)の
        # dataclassでも cls() の生な TypeError ではなく SchemaError で弾ける。
        self._spec = introspect(cls)
        initial = model() if isinstance(model, type) else model
        if theme is not None:
            mode = None if theme == "auto" else theme
            theme_mod.apply_theme(self, mode)
        self.palette = theme_mod.current_palette(self)
        self.motion = (not motion_mod.prefers_reduced_motion()) if motion is None else motion
        self._on_change = on_change
        self._suspend_notify = True
        self._root = _GroupWidget(self, self._spec, self, is_root=True)
        self.set(initial)
        self._suspend_notify = False

    def get(self) -> Any:
        """入力値をdataclassインスタンスとして返す。不正ならFormValidationError。"""
        errors: list[FieldError] = []
        value = self._root.value("", errors)
        if errors:
            raise FormValidationError(errors)
        return value

    def set(self, instance: Any) -> None:
        """インスタンスの値をフォームに反映する。"""
        self._suspend_notify = True
        try:
            self._root.set(instance)
        finally:
            self._suspend_notify = False

    def notify(self) -> None:
        if not self._suspend_notify and self._on_change is not None:
            self._on_change()


class _FieldWidget:
    """1フィールド分のラベル・入力・補足・エラー表示の組。"""

    def __init__(self, form: Form, spec: FieldSpec, parent: ttk.Frame, row: int) -> None:
        self.form = form
        self.spec = spec
        self.rows = 2
        # 不正表示の対象。ttk入力はスタイル差し替え、tk.Text/Listboxは枠色で示す。
        self.invalid_target: tk.Widget | None = None
        self.invalid_style: str | None = None
        gap = theme_mod.SPACE_SM
        label = ttk.Label(parent, text=spec.label, style="Field.TLabel")
        label.grid(row=row, column=0, sticky="nw", padx=(0, theme_mod.SPACE_MD), pady=(gap, 0))
        self.control = self._build_control(parent)
        self.control.grid(row=row, column=1, sticky="ew", pady=(gap, 0))
        next_row = row + 1
        if spec.help:
            help_label = ttk.Label(parent, text=spec.help, style="Help.TLabel")
            help_label.grid(row=next_row, column=1, sticky="w", pady=(theme_mod.SPACE_XS, 0))
            next_row += 1
            self.rows += 1
        self.error_label = ttk.Label(parent, text="", style="Error.TLabel")
        self.error_label.grid(row=next_row, column=1, sticky="w", pady=(theme_mod.SPACE_XS, 0))
        self.error_label.grid_remove()

    def _build_control(self, parent: ttk.Frame) -> tk.Widget:
        raise NotImplementedError

    def raw(self) -> Any:
        raise NotImplementedError

    def set_value(self, value: Any) -> None:
        raise NotImplementedError

    def show_error(self, message: str | None) -> None:
        if message is None:
            self.error_label.grid_remove()
        else:
            self.error_label.configure(text=message)
            self.error_label.grid()
        self._mark_invalid(message is not None)

    def _mark_invalid(self, invalid: bool) -> None:
        """入力欄に不正状態の見た目を着せる/外す。テーマ未適用なら何もしない。"""
        target = self.invalid_target
        if target is None or self.form.palette is None:
            return
        if self.invalid_style is not None:
            style = f"Invalid.{self.invalid_style}" if invalid else self.invalid_style
            target.configure(style=style)
        else:
            palette = self.form.palette
            edge = palette.error if invalid else palette.border
            target.configure(highlightbackground=edge, highlightcolor=edge)

    def _traced_var(self, var: tk.Variable) -> tk.Variable:
        var.trace_add("write", lambda *_: self.form.notify())
        return var


class _BoolWidget(_FieldWidget):
    def _build_control(self, parent: ttk.Frame) -> tk.Widget:
        self.var = self._traced_var(tk.BooleanVar(parent))
        return ttk.Checkbutton(parent, variable=self.var)

    def raw(self) -> bool:
        return self.var.get()

    def set_value(self, value: Any) -> None:
        self.var.set(bool(value))


class _NumberWidget(_FieldWidget):
    def _build_control(self, parent: ttk.Frame) -> tk.Widget:
        self.var = self._traced_var(tk.StringVar(parent))
        is_float = self.spec.kind == "float"
        rng = self.spec.range
        increment = rng.step if rng and rng.step else (0.1 if is_float else 1)
        spinbox = ttk.Spinbox(
            parent,
            textvariable=self.var,
            from_=rng.min if rng else -1_000_000_000,
            to=rng.max if rng else 1_000_000_000,
            increment=increment,
            width=14,
        )
        self.invalid_target, self.invalid_style = spinbox, "TSpinbox"
        return spinbox

    def raw(self) -> str:
        return self.var.get()

    def set_value(self, value: Any) -> None:
        self.var.set(str(value))


class _ChoiceWidget(_FieldWidget):
    def _build_control(self, parent: ttk.Frame) -> tk.Widget:
        assert self.spec.choices is not None
        self.var = self._traced_var(tk.StringVar(parent))
        values = [display_choice(self.spec, c) for c in self.spec.choices]
        combo = ttk.Combobox(parent, textvariable=self.var, values=values, state="readonly")
        self.invalid_target, self.invalid_style = combo, "TCombobox"
        return combo

    def raw(self) -> str:
        return self.var.get()

    def set_value(self, value: Any) -> None:
        self.var.set(display_choice(self.spec, value))


class _TextWidget(_FieldWidget):
    def _build_control(self, parent: ttk.Frame) -> tk.Widget:
        self.var = self._traced_var(tk.StringVar(parent))
        entry = ttk.Entry(parent, textvariable=self.var, show="*" if self.spec.secret else "")
        self.invalid_target, self.invalid_style = entry, "TEntry"
        return entry

    def raw(self) -> str:
        return self.var.get()

    def set_value(self, value: Any) -> None:
        self.var.set(str(value))


class _MultilineWidget(_FieldWidget):
    def _build_control(self, parent: ttk.Frame) -> tk.Widget:
        assert self.spec.multiline is not None
        self.text = tk.Text(parent, height=self.spec.multiline.height, width=40)
        if self.form.palette is not None:
            theme_mod.style_text(self.text, self.form.palette)
        self.text.bind("<KeyRelease>", lambda _e: self.form.notify())
        self.invalid_target = self.text  # tk.Textは枠色で不正を示す
        return self.text

    def raw(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_value(self, value: Any) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", str(value))


class _PathWidget(_FieldWidget):
    def _build_control(self, parent: ttk.Frame) -> tk.Widget:
        frame = ttk.Frame(parent)
        self.var = self._traced_var(tk.StringVar(parent))
        entry = ttk.Entry(frame, textvariable=self.var)
        entry.pack(side="left", fill="x", expand=True)
        button = ttk.Button(frame, text="参照", command=self._browse, width=6)
        button.pack(side="left", padx=(theme_mod.SPACE_SM, 0))
        self.invalid_target, self.invalid_style = entry, "TEntry"
        return frame

    def _browse(self) -> None:
        if self.spec.path_select == "dir":
            chosen = filedialog.askdirectory()
        else:
            patterns = list(self.spec.file_patterns) or [("すべてのファイル", "*")]
            chosen = filedialog.askopenfilename(filetypes=patterns)
        if chosen:
            self.var.set(chosen)

    def raw(self) -> str:
        return self.var.get()

    def set_value(self, value: Any) -> None:
        self.var.set(str(value))


class _StrListWidget(_FieldWidget):
    def _build_control(self, parent: ttk.Frame) -> tk.Widget:
        frame = ttk.Frame(parent)
        self.listbox = tk.Listbox(frame, height=4, activestyle="none")
        if self.form.palette is not None:
            theme_mod.style_text(self.listbox, self.form.palette)
        self.invalid_target = self.listbox  # tk.Listboxは枠色で不正を示す
        self.listbox.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.entry_var = tk.StringVar(parent)
        entry = ttk.Entry(frame, textvariable=self.entry_var)
        entry.grid(row=1, column=0, sticky="ew", pady=(theme_mod.SPACE_XS, 0))
        entry.bind("<Return>", lambda _e: self._add())
        add = ttk.Button(frame, text="追加", command=self._add, width=6)
        add.grid(row=1, column=1, padx=(theme_mod.SPACE_SM, 0), pady=(theme_mod.SPACE_XS, 0))
        remove = ttk.Button(frame, text="削除", command=self._remove, width=6)
        remove.grid(row=1, column=2, padx=(theme_mod.SPACE_SM, 0), pady=(theme_mod.SPACE_XS, 0))
        frame.columnconfigure(0, weight=1)
        return frame

    def _add(self) -> None:
        text = self.entry_var.get().strip()
        if text:
            self.listbox.insert("end", text)
            self.entry_var.set("")
            self.form.notify()

    def _remove(self) -> None:
        for index in reversed(self.listbox.curselection()):
            self.listbox.delete(index)
        self.form.notify()

    def raw(self) -> list[str]:
        return list(self.listbox.get(0, "end"))

    def set_value(self, value: Any) -> None:
        self.listbox.delete(0, "end")
        for item in value:
            self.listbox.insert("end", str(item))


_WIDGETS: dict[str, type[_FieldWidget]] = {
    "bool": _BoolWidget,
    "int": _NumberWidget,
    "float": _NumberWidget,
    "choice": _ChoiceWidget,
    "path": _PathWidget,
    "str_list": _StrListWidget,
}


def _widget_class(spec: FieldSpec) -> type[_FieldWidget]:
    if spec.kind == "text":
        return _MultilineWidget if spec.multiline else _TextWidget
    return _WIDGETS[spec.kind]


class _GroupWidget:
    """ネストしたdataclassをLabelFrameとして描く。"""

    def __init__(
        self, form: Form, spec: FieldSpec, parent: ttk.Frame, *, is_root: bool = False
    ) -> None:
        self.spec = spec
        self.children: dict[str, _FieldWidget | _GroupWidget] = {}
        if is_root:
            container: ttk.Frame = parent
        else:
            container = ttk.LabelFrame(parent, text=spec.label, padding=theme_mod.SPACE_MD)
        self.container = container
        container.columnconfigure(1, weight=1)
        row = 0
        for child in spec.children:
            if child.kind == "group":
                group = _GroupWidget(form, child, container)
                group.container.grid(
                    row=row, column=0, columnspan=2, sticky="ew", pady=(theme_mod.SPACE_MD, 0)
                )
                self.children[child.name] = group
                row += 1
            else:
                widget = _widget_class(child)(form, child, container, row)
                self.children[child.name] = widget
                row += widget.rows

    def grid(self, **kwargs: Any) -> None:
        self.container.grid(**kwargs)

    def value(self, prefix: str, errors: list[FieldError]) -> Any:
        assert self.spec.group_type is not None
        kwargs: dict[str, Any] = {}
        for name, child in self.children.items():
            path = f"{prefix}{name}"
            if isinstance(child, _GroupWidget):
                kwargs[name] = child.value(f"{path}.", errors)
                continue
            try:
                kwargs[name] = coerce_field(child.spec, child.raw())
                child.show_error(None)
            except ValueError as error:
                child.show_error(str(error))
                errors.append(FieldError(path=path, label=child.spec.label, message=str(error)))
        if errors:
            return None
        return self.spec.group_type(**kwargs)

    def set(self, instance: Any) -> None:
        for field in dataclasses.fields(instance):
            child = self.children.get(field.name)
            if child is None:
                continue
            value = getattr(instance, field.name)
            if isinstance(child, _GroupWidget):
                child.set(value)
            else:
                child.set_value(value)
