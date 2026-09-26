"""Fluent-style design tokens for the Upbit desktop UI.

Single source of truth for spacing, control sizing, typography and
semantic colors (DESKTOP_UI_DESIGN_RULES.md section 5-7).

Rules:
- spacing uses only the 4/8/12/16/24/32 scale
- pages never hard-code hex colors; they import semantic tokens here
- ``dark`` variants are selected centrally by ``upbit_autotrader.ui.theme``
"""

from __future__ import annotations

# --- spacing scale (only these values) -------------------------------------
SPACE_XXS = 4
SPACE_XS = 8
SPACE_SM = 12
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 32

# --- control sizing ---------------------------------------------------------
CONTROL_HEIGHT_SM = 32
CONTROL_HEIGHT_MD = 36
CONTROL_HEIGHT_LG = 40

PAGE_MARGIN = 24
SECTION_GAP = 24
CARD_RADIUS = 8

# --- typography (px) ---------------------------------------------------------
FONT_PAGE_TITLE = 22
FONT_SECTION_TITLE = 16
FONT_BODY = 13
FONT_SECONDARY = 12
FONT_CAPTION = 11

FONT_FAMILY = "'Pretendard','Segoe UI','Apple SD Gothic Neo','Malgun Gothic',sans-serif"

# --- accent (single primary accent per screen) --------------------------------
ACCENT = "#2f7cf6"

# --- chart colors (painted widget, theme-aware) --------------------------------
_CHART_DARK = {
    "background": "#101020",
    "grid": "#888888",
    "text": "#bbbbbb",
}
_CHART_LIGHT = {
    "background": "#ffffff",
    "grid": "#9aa3b2",
    "text": "#5b6776",
}


def chart_colors(dark: bool) -> dict:
    """Background/grid/text colors for the dependency-free price chart."""
    return dict(_CHART_DARK if dark else _CHART_LIGHT)


# --- domain colors (trading semantics only: up/buy vs down/sell) --------------
TRADE_BUY = "#e63946"
TRADE_BUY_HOVER = "#d62839"
TRADE_SELL = "#4361ee"
TRADE_SELL_HOVER = "#3a55d6"

# --- semantic colors: light / dark --------------------------------------------
_LIGHT = {
    "primary": ACCENT,
    "background": "#f3f5f9",
    "surface": "#ffffff",
    "surface_alt": "#eef1f6",
    "border": "#d4dae3",
    "text_primary": "#1b2430",
    "text_secondary": "#5b6776",
    "success": "#1b7f3b",
    "warning": "#9a6200",
    "error": "#c22e2e",
    "info": "#2f7cf6",
}

_DARK = {
    "primary": ACCENT,
    "background": "#0f172a",
    "surface": "#16213e",
    "surface_alt": "#111827",
    "border": "#334155",
    "text_primary": "#e2e8f0",
    "text_secondary": "#93a0b4",
    "success": "#4caf50",
    "warning": "#ffc107",
    "error": "#f87171",
    "info": "#00b4d8",
}


def palette(dark: bool) -> dict:
    """Return the semantic color mapping for the active theme."""
    return dict(_DARK if dark else _LIGHT)


def status_color(kind: str, dark: bool) -> str:
    """Semantic color for a status kind: success|warning|error|info|neutral."""
    colors = palette(dark)
    if kind in colors:
        return colors[kind]
    return colors["text_secondary"]
