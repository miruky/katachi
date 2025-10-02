"""実ウィジェットを使ったフォームの往復テスト。

CIではxvfb上で動かす。ディスプレイがない環境では自動でスキップする。
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Annotated

import pytest

tk = pytest.importorskip("tkinter", reason="tkinterなしのビルドではスキップ")

import datetime  # noqa: E402

from katachi import FormValidationError, Range, SchemaError, Secret  # noqa: E402
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


def test_reset_restores_defaults_and_clears_errors(root: tk.Tk):
    form = Form(root, Settings, theme="light")
    form.set(Settings(workers=16, name="renamed"))
    workers = form._root.children["workers"]
    workers.set_value("999")
    with pytest.raises(FormValidationError):
        form.get()
    assert "Invalid" in workers.control.cget("style")
    form.reset()
    assert form.get() == Settings()
    assert "Invalid" not in workers.control.cget("style")


def test_date_field_round_trips(root: tk.Tk):
    @dataclass
    class HasDate:
        start: datetime.date = datetime.date(2026, 1, 1)
        name: str = "x"

    form = Form(root, HasDate, theme=None)
    form.set(HasDate(start=datetime.date(2030, 12, 31)))
    assert form.get() == HasDate(start=datetime.date(2030, 12, 31))


def test_invalid_date_reports_field_error(root: tk.Tk):
    @dataclass
    class HasDate:
        start: datetime.date = datetime.date(2026, 1, 1)

    form = Form(root, HasDate, theme=None)
    form._root.children["start"].set_value("2030/12/31")
    with pytest.raises(FormValidationError) as excinfo:
        form.get()
    assert any(e.path == "start" for e in excinfo.value.errors)


def test_secret_reveal_toggle(root: tk.Tk):
    @dataclass
    class HasSecret:
        token: Annotated[str, Secret()] = ""

    form = Form(root, HasSecret, theme=None)
    widget = form._root.children["token"]
    assert widget.entry.cget("show") == "*"
    widget._toggle_reveal()
    assert widget.entry.cget("show") == ""
    widget._toggle_reveal()
    assert widget.entry.cget("show") == "*"


def test_focus_invalid_targets_first_error_in_order(root: tk.Tk):
    form = Form(root, Settings, theme="light")
    form._root.children["workers"].set_value("999")
    form._root.children["network"].children["port"].set_value("0")
    with pytest.raises(FormValidationError):
        form.get()
    # 配置順で先に来るworkersが選ばれる(network.portより前)。
    assert form.focus_invalid() is form._root.children["workers"]


def test_focus_invalid_returns_none_when_valid(root: tk.Tk):
    form = Form(root, Settings, theme="light")
    form.get()
    assert form.focus_invalid() is None


def test_empty_dataclass_renders_and_validates(root: tk.Tk):
    @dataclass
    class Empty:
        pass

    form = Form(root, Empty, theme="light")
    assert form.get() == Empty()
    assert form.focus_invalid() is None


def test_is_valid_is_non_destructive(root: tk.Tk):
    form = Form(root, Settings, theme="light")
    workers = form._root.children["workers"]
    workers.set_value("999")
    assert form.is_valid() is False
    # 非破壊: 確認しただけではエラー表示も不正スタイルも出さない。
    assert workers.has_error is False
    assert "Invalid" not in workers.control.cget("style")
    workers.set_value("8")
    assert form.is_valid() is True


def test_str_list_delete_key_removes_selection(root: tk.Tk):
    form = Form(root, Settings, theme="light")
    tags = form._root.children["tags"]
    tags.set_value(["a", "b", "c"])
    # macOSの主要な削除キーは<BackSpace>、それ以外は<Delete>を送る。両方拾う。
    assert tags.listbox.bind("<Delete>")
    assert tags.listbox.bind("<BackSpace>")
    tags.listbox.selection_set(1)
    assert tags._on_delete_key(None) == "break"  # 既定操作を止める
    assert tags.raw() == ["a", "c"]


def test_date_range_rejects_out_of_bounds(root: tk.Tk):
    @dataclass
    class Booking:
        day: Annotated[
            datetime.date, Range(datetime.date(2026, 1, 1), datetime.date(2026, 12, 31))
        ] = datetime.date(2026, 6, 1)

    form = Form(root, Booking, theme=None)
    form._root.children["day"].set_value("2027-03-01")
    with pytest.raises(FormValidationError) as excinfo:
        form.get()
    assert any(e.path == "day" for e in excinfo.value.errors)
    # 範囲内に直せば通る。
    form._root.children["day"].set_value("2026-03-01")
    assert form.get() == Booking(day=datetime.date(2026, 3, 1))
