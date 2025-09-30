"""dataclass定義をフィールド仕様の木に変換するイントロスペクション。"""

from __future__ import annotations

import dataclasses
import datetime
from dataclasses import MISSING, dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, get_args, get_origin, get_type_hints

from .errors import SchemaError
from .markers import Choices, DirPath, FilePath, Help, Label, Multiline, Range, Secret

Kind = Literal["bool", "int", "float", "text", "choice", "path", "date", "str_list", "group"]


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """1フィールド分の仕様。kind == "group" のときだけchildrenを持つ。"""

    name: str
    label: str
    kind: Kind
    default: Any
    help: str | None = None
    range: Range | None = None
    choices: tuple[Any, ...] | None = None
    enum_type: type[Enum] | None = None
    multiline: Multiline | None = None
    secret: bool = False
    path_select: Literal["file", "dir"] | None = None
    file_patterns: tuple[tuple[str, str], ...] = ()
    group_type: type | None = None
    children: tuple[FieldSpec, ...] = ()


def introspect(cls: type) -> FieldSpec:
    """dataclassをルートグループのFieldSpecに変換する。"""
    if not (isinstance(cls, type) and dataclasses.is_dataclass(cls)):
        raise SchemaError(f"{cls!r} はdataclassではない")
    hints = get_type_hints(cls, include_extras=True)
    children = tuple(_field_spec(field, hints[field.name]) for field in dataclasses.fields(cls))
    return FieldSpec(
        name=cls.__name__,
        label=_labelize(cls.__name__),
        kind="group",
        default=None,
        group_type=cls,
        children=children,
    )


def _labelize(name: str) -> str:
    return name.replace("_", " ")


def _default_of(field: dataclasses.Field[Any]) -> Any:
    if field.default is not MISSING:
        return field.default
    if field.default_factory is not MISSING:
        return field.default_factory()
    raise SchemaError(f"フィールド '{field.name}' にはデフォルト値が必要")


def _field_spec(field: dataclasses.Field[Any], hint: Any) -> FieldSpec:
    base = hint
    metadata: tuple[Any, ...] = ()
    if get_origin(hint) is Annotated:
        base, *rest = get_args(hint)
        metadata = tuple(rest)

    label = next((m.text for m in metadata if isinstance(m, Label)), _labelize(field.name))
    help_ = next((m.text for m in metadata if isinstance(m, Help)), None)
    range_ = next((m for m in metadata if isinstance(m, Range)), None)
    choices_marker = next((m for m in metadata if isinstance(m, Choices)), None)
    multiline = next((m for m in metadata if isinstance(m, Multiline)), None)
    secret = any(isinstance(m, Secret) for m in metadata)
    file_marker = next((m for m in metadata if isinstance(m, FilePath)), None)
    dir_marker = next((m for m in metadata if isinstance(m, DirPath)), None)

    common: dict[str, Any] = {
        "name": field.name,
        "label": label,
        "default": _default_of(field),
        "help": help_,
        "range": range_,
        "multiline": multiline,
        "secret": secret,
    }

    if isinstance(base, type) and dataclasses.is_dataclass(base):
        nested = introspect(base)
        return FieldSpec(kind="group", group_type=base, children=nested.children, **common)

    if get_origin(base) is Literal:
        return FieldSpec(kind="choice", choices=get_args(base), **common)

    if isinstance(base, type) and issubclass(base, Enum):
        return FieldSpec(kind="choice", choices=tuple(base), enum_type=base, **common)

    if choices_marker is not None:
        if base not in (str, int):
            raise SchemaError(f"Choicesはstr/intにのみ使える: '{field.name}'")
        return FieldSpec(kind="choice", choices=choices_marker.values, **common)

    if base is bool:
        return FieldSpec(kind="bool", **common)
    if base is int:
        return FieldSpec(kind="int", **common)
    if base is float:
        return FieldSpec(kind="float", **common)
    if base is str:
        return FieldSpec(kind="text", **common)
    if base is datetime.date:
        return FieldSpec(kind="date", **common)
    if base is Path:
        select: Literal["file", "dir"] = "dir" if dir_marker is not None else "file"
        return FieldSpec(
            kind="path",
            path_select=select,
            file_patterns=file_marker.patterns if file_marker else (),
            **common,
        )
    if get_origin(base) is list and get_args(base) == (str,):
        return FieldSpec(kind="str_list", **common)

    raise SchemaError(f"未対応の型 {base!r}: フィールド '{field.name}'")
