from __future__ import annotations

import sys

from matplotlib import rcParams


def configure_japanese_matplotlib() -> str:
    """Use one known font per platform; never scan the user's system fonts."""

    selected = "Yu Gothic" if sys.platform == "win32" else "Noto Sans CJK JP"
    rcParams["font.family"] = "sans-serif"
    rcParams["font.sans-serif"] = [selected, "DejaVu Sans"]
    rcParams["axes.unicode_minus"] = False
    return selected
