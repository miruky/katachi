"""Annotatedの第二引数以降に付けるメタデータマーカー。

typing.Annotatedを通じてフィールドに意味づけを与える。

    workers: Annotated[int, Range(1, 32), Help("並列処理数")] = 4
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Range:
    """数値の下限・上限。stepはスピンボックスの増分になる。"""

    min: float
    max: float
    step: float | None = None


class Choices:
    """選択肢を列挙する。strとintのフィールドに使える。"""

    __slots__ = ("values",)

    def __init__(self, *values: object) -> None:
        if not values:
            raise ValueError("Choicesには1つ以上の値が必要")
        self.values: tuple[object, ...] = values


@dataclass(frozen=True, slots=True)
class Help:
    """フィールドの下に表示する補足説明。"""

    text: str


@dataclass(frozen=True, slots=True)
class Label:
    """表示ラベル。未指定ならフィールド名から導出する。"""

    text: str


@dataclass(frozen=True, slots=True)
class Multiline:
    """複数行テキスト入力にする。strのフィールドに使える。"""

    height: int = 5


@dataclass(frozen=True, slots=True)
class Secret:
    """入力を伏せ字にする。strのフィールドに使える。"""


@dataclass(frozen=True, slots=True)
class FilePath:
    """ファイル選択ダイアログ付きのパス入力にする。

    patternsはtkinterのfiletypes形式: (("画像", "*.png"), ...)
    """

    patterns: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class DirPath:
    """ディレクトリ選択ダイアログ付きのパス入力にする。"""
