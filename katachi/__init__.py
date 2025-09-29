"""katachi: dataclassと型ヒントから設定画面を生成する宣言型GUIライブラリ。

標準ライブラリのみで動く。典型的な使い方:

    from dataclasses import dataclass
    from typing import Annotated
    import katachi
    from katachi import Help, Range

    @dataclass
    class Settings:
        workers: Annotated[int, Range(1, 32), Help("並列処理数")] = 4
        verbose: bool = False

    settings = katachi.edit(Settings, store="~/.config/myapp.json")
"""

from .errors import (
    FieldError,
    FormValidationError,
    KatachiError,
    PersistenceError,
    SchemaError,
)
from .markers import Choices, DirPath, FilePath, Help, Label, Multiline, Range, Secret
from .persistence import build, load, save, to_jsonable
from .schema import FieldSpec, introspect

__version__ = "0.1.0"

__all__ = [
    "Choices",
    "DirPath",
    "FieldError",
    "FieldSpec",
    "FilePath",
    "Form",
    "FormValidationError",
    "Help",
    "KatachiError",
    "Label",
    "Multiline",
    "PersistenceError",
    "Range",
    "SchemaError",
    "Secret",
    "__version__",
    "build",
    "edit",
    "introspect",
    "load",
    "save",
    "to_jsonable",
]


def __getattr__(name: str) -> object:
    # tkinterはGUIを使う時だけ読み込む。ヘッドレス環境でも
    # スキーマ・検証・永続化を使えるようにするための遅延import
    if name in ("Form", "edit"):
        from . import tk as _tk

        return getattr(_tk, name)
    raise AttributeError(f"module 'katachi' has no attribute {name!r}")
