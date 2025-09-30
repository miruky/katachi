"""introspectの型マッピングとメタデータ抽出のテスト。"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

import pytest

from katachi import Choices, DirPath, Help, Label, Multiline, Range, SchemaError, Secret, introspect


class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"


@dataclass
class Nested:
    host: str = "localhost"
    port: Annotated[int, Range(1, 65535)] = 8080


@dataclass
class Sample:
    enabled: bool = True
    workers: Annotated[int, Range(1, 32, step=1), Help("並列処理数")] = 4
    ratio: float = 0.5
    name: Annotated[str, Label("表示名")] = "miruky"
    token: Annotated[str, Secret()] = ""
    memo: Annotated[str, Multiline(height=3)] = ""
    theme: Theme = Theme.LIGHT
    mode: Literal["fast", "safe"] = "safe"
    quality: Annotated[str, Choices("low", "high")] = "low"
    log_dir: Annotated[Path, DirPath()] = Path("logs")
    tags: list[str] = field(default_factory=list)
    network: Nested = field(default_factory=Nested)


def spec_of(name: str):
    root = introspect(Sample)
    return next(s for s in root.children if s.name == name)


def test_kinds_are_mapped():
    assert spec_of("enabled").kind == "bool"
    assert spec_of("workers").kind == "int"
    assert spec_of("ratio").kind == "float"
    assert spec_of("name").kind == "text"
    assert spec_of("log_dir").kind == "path"
    assert spec_of("tags").kind == "str_list"
    assert spec_of("network").kind == "group"


def test_metadata_is_extracted():
    workers = spec_of("workers")
    assert workers.range is not None
    assert workers.range.min == 1
    assert workers.range.max == 32
    assert workers.help == "並列処理数"
    assert spec_of("name").label == "表示名"
    assert spec_of("token").secret is True
    assert spec_of("memo").multiline is not None
    assert spec_of("memo").multiline.height == 3


def test_label_falls_back_to_field_name():
    assert spec_of("log_dir").label == "log dir"


def test_enum_and_literal_become_choices():
    theme = spec_of("theme")
    assert theme.kind == "choice"
    assert theme.enum_type is Theme
    assert theme.choices == (Theme.LIGHT, Theme.DARK)

    mode = spec_of("mode")
    assert mode.kind == "choice"
    assert mode.choices == ("fast", "safe")

    quality = spec_of("quality")
    assert quality.kind == "choice"
    assert quality.choices == ("low", "high")


def test_dir_marker_sets_path_select():
    assert spec_of("log_dir").path_select == "dir"


def test_nested_group_has_children():
    network = spec_of("network")
    assert network.group_type is Nested
    assert [c.name for c in network.children] == ["host", "port"]


def test_defaults_are_captured():
    assert spec_of("workers").default == 4
    assert spec_of("tags").default == []


def test_non_dataclass_is_rejected():
    with pytest.raises(SchemaError):
        introspect(int)


def test_field_without_default_is_rejected():
    @dataclass
    class NoDefault:
        value: int

    with pytest.raises(SchemaError):
        introspect(NoDefault)


def test_unsupported_type_is_rejected():
    @dataclass
    class Unsupported:
        data: dict[str, int] = field(default_factory=dict)

    with pytest.raises(SchemaError):
        introspect(Unsupported)


def test_choices_on_wrong_type_is_rejected():
    @dataclass
    class Wrong:
        flag: Annotated[bool, Choices(True, False)] = True

    with pytest.raises(SchemaError):
        introspect(Wrong)


def test_date_maps_to_date_kind():
    import datetime

    @dataclass
    class WithDate:
        start: datetime.date = datetime.date(2026, 1, 1)

    spec = next(s for s in introspect(WithDate).children if s.name == "start")
    assert spec.kind == "date"
