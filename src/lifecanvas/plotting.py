from __future__ import annotations

from matplotlib import font_manager, rcParams


_JAPANESE_FONT_CANDIDATES = (
    "Yu Gothic",
    "YuGothic",
    "Meiryo",
    "MS Gothic",
    "Noto Sans CJK JP",
    "Noto Sans JP",
    "IPAexGothic",
    "IPAGothic",
)


def configure_japanese_matplotlib() -> str | None:
    """Select a Japanese-capable system font without bundling font files."""

    selected: str | None = None
    for family in _JAPANESE_FONT_CANDIDATES:
        try:
            font_manager.findfont(
                font_manager.FontProperties(family=family),
                fallback_to_default=False,
            )
        except ValueError:
            continue
        selected = family
        break

    if selected:
        rcParams["font.family"] = selected
        rcParams["font.sans-serif"] = [
            selected,
            *_JAPANESE_FONT_CANDIDATES,
            "DejaVu Sans",
        ]
    else:
        rcParams["font.sans-serif"] = [
            *_JAPANESE_FONT_CANDIDATES,
            "DejaVu Sans",
        ]
    rcParams["axes.unicode_minus"] = False
    return selected
