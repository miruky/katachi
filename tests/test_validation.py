"""coerce_fieldの変換と検証メッセージのテスト。"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Annotated

import pytest

from katachi import Range, introspect
from katachi.validation import coerce_field, display_choice


class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"


@dataclass
class Sample:
    workers: Annotated[int, Range(1, 32)] = 4
    ratio: float = 0.5
    theme: Theme = Theme.LIGHT
    log_dir: Path = Path("logs")
    tags: list[str] = field(default_factory=list)


def spec_of(name: str):
    return next(s for s in introspect(Sample).children if s.name == name)


def test_int_coercion_strips_and_converts():
    assert coerce_field(spec_of("workers"), " 8 ") == 8


def test_int_rejects_garbage_with_message():
    with pytest.raises(ValueError, match="整数"):
        coerce_field(spec_of("workers"), "abc")
    with pytest.raises(ValueError, match="整数"):
        coerce_field(spec_of("workers"), "")


def test_range_is_enforced():
    with pytest.raises(ValueError, match="1以上32以下"):
        coerce_field(spec_of("workers"), "0")
    with pytest.raises(ValueError, match="1以上32以下"):
        coerce_field(spec_of("workers"), "33")
    assert coerce_field(spec_of("workers"), "32") == 32


def test_float_coercion():
    assert coerce_field(spec_of("ratio"), "0.25") == 0.25
    with pytest.raises(ValueError, match="数値"):
        coerce_field(spec_of("ratio"), "x")


def test_choice_accepts_display_string_and_value():
    assert coerce_field(spec_of("theme"), "DARK") is Theme.DARK
    assert coerce_field(spec_of("theme"), Theme.LIGHT) is Theme.LIGHT
    with pytest.raises(ValueError, match="選択肢"):
        coerce_field(spec_of("theme"), "BLUE")


def test_display_choice_uses_enum_name():
    assert display_choice(spec_of("theme"), Theme.DARK) == "DARK"


def test_path_requires_non_empty():
    assert coerce_field(spec_of("log_dir"), "data/logs") == Path("data/logs")
    with pytest.raises(ValueError, match="パス"):
        coerce_field(spec_of("log_dir"), "  ")


def test_str_list_drops_blank_entries():
    assert coerce_field(spec_of("tags"), ["a", " ", "b"]) == ["a", "b"]
    with pytest.raises(ValueError, match="リスト"):
        coerce_field(spec_of("tags"), "not-a-list")


def _date_spec():
    import datetime

    @dataclass
    class WithDate:
        start: datetime.date = datetime.date(2026, 1, 1)

    return next(s for s in introspect(WithDate).children if s.name == "start")


def test_coerce_date_parses_iso():
    import datetime

    assert coerce_field(_date_spec(), "2030-12-31") == datetime.date(2030, 12, 31)


def test_coerce_date_rejects_bad_format():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        coerce_field(_date_spec(), "2030/12/31")

    with pytest.raises(ValueError, match="日付"):
        coerce_field(_date_spec(), "   ")
