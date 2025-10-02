"""tkinterバックエンド。"""

from .dialog import edit
from .form import Form
from .scroll import ScrollableFrame
from .theme import Palette, apply_theme, current_palette, detect_mode

__all__ = [
    "Form",
    "Palette",
    "ScrollableFrame",
    "apply_theme",
    "current_palette",
    "detect_mode",
    "edit",
]
