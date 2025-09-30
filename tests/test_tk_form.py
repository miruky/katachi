"""実ウィジェットを使ったフォームの往復テスト。

CIではxvfb上で動かす。ディスプレイがない環境では自動でスキップする。
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Annotated

import pytest

tk = pytest.importorskip("tkinter", reason="tkinterなしのビルドではスキップ")

from katachi import FormValidationError, Range, SchemaError  # noqa: E402
from katachi.tk import Form  # noqa: E402


class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"


@dataclass
class Network:
    host: str = "localhost"
    port: Annotated[int, Range(1, 65535)] = 8080


@dataclass
class Settings:
    enabled: bool = True
    workers: Annotated[int, Range(1, 32)] = 4
    theme: Theme = Theme.LIGHT
    name: str = "app"
    log_dir: Path = Path("logs")
    tags: list[str] = field(default_factory=lambda: ["default"])
    network: Network = field(default_factory=Network)


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("ディスプレイがないためスキップ")
    window.withdraw()
    yield window
    window.destroy()


def test_form_round_trip(root: tk.Tk):
    value = Settings(
        enabled=False,
        workers=16,
        theme=Theme.DARK,
        name="renamed",
        log_dir=Path("/tmp/logs"),
        tags=["a", "b"],
        network=Network(host="example.com", port=443),
    )
    form = Form(root, Settings)
    form.set(value)
    assert form.get() == value


def test_form_starts_with_defaults(root: tk.Tk):
    form = Form(root, Settings)
    assert form.get() == Settings()


def test_invalid_input_raises_with_field_path(root: tk.Tk):
    form = Form(root, Settings)
    form.set(Settings())
    # 範囲外の値を直接流し込む
    workers_widget = form._root.children["workers"]
    workers_widget.set_value("99")
    with pytest.raises(FormValidationError) as excinfo:
        form.get()
    assert any(e.path == "workers" for e in excinfo.value.errors)

    nested = form._root.children["network"]
    nested.children["port"].set_value("0")
    with pytest.raises(FormValidationError) as excinfo:
        form.get()
    assert any(e.path == "network.port" for e in excinfo.value.errors)


def test_on_change_fires(root: tk.Tk):
    calls: list[int] = []
    form = Form(root, Settings, on_change=lambda: calls.append(1))
    assert calls == []
    form._root.children["name"].set_value("changed")
    assert calls != []


def test_form_applies_requested_theme(root: tk.Tk):
    from katachi.tk.theme import DARK

    form = Form(root, Settings, theme="dark")
    assert form.palette is DARK


def test_form_theme_none_leaves_palette_unset(root: tk.Tk):
    form = Form(root, Settings, theme=None)
    assert form.palette is None
    # スタイルに触れなくても入力の往復は壊れない。
    assert form.get() == Settings()


def test_required_field_dataclass_raises_schema_error(root: tk.Tk):
    @dataclass
    class NeedsArg:
        required: int  # デフォルト値が無い
        name: str = "x"

    with pytest.raises(SchemaError):
        Form(root, NeedsArg)


def test_invalid_field_toggles_invalid_style(root: tk.Tk):
    form = Form(root, Settings, theme="light")
    workers = form._root.children["workers"]
    workers.set_value("999")  # 範囲外
    with pytest.raises(FormValidationError):
        form.get()
    assert "Invalid" in workers.control.cget("style")
    # 直せば不正スタイルが外れる。
    workers.set_value("8")
    form.get()
    assert "Invalid" not in workers.control.cget("style")
