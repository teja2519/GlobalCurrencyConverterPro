"""
utils/constants.py

Centralised visual constants: color palette (dark + light), fonts, spacing
and window sizing. Keeping these in one place is what lets every UI panel
share a single consistent, professional look.
"""

APP_NAME = "Global Currency Converter Pro"
APP_SUBTITLE = "Live Exchange Rates Powered by Online API"
APP_VERSION = "1.0.0"

MIN_WIDTH = 700
MIN_HEIGHT = 800

CORNER_RADIUS = 14
PAD = 14

FONT_FAMILY = "Segoe UI"

# ---------------------------------------------------------------- DARK THEME
DARK = {
    "bg":            "#0F1115",
    "surface":       "#171A21",
    "surface_alt":   "#1F232C",
    "card":          "#20252F",
    "border":        "#2A2F3A",
    "accent":        "#5B8DEF",
    "accent_hover":  "#4A78D6",
    "accent_soft":   "#23304A",
    "success":       "#3DD68C",
    "danger":        "#F1556C",
    "warning":       "#F4C144",
    "text":          "#F5F6FA",
    "text_dim":      "#9AA3B2",
    "text_faint":    "#6B7280",
}

# --------------------------------------------------------------- LIGHT THEME
LIGHT = {
    "bg":            "#F4F6FB",
    "surface":       "#FFFFFF",
    "surface_alt":   "#EDF0F7",
    "card":          "#FFFFFF",
    "border":        "#DDE2EC",
    "accent":        "#3D6BE0",
    "accent_hover":  "#2F57C2",
    "accent_soft":   "#E4ECFE",
    "success":       "#1FA866",
    "danger":        "#D8344E",
    "warning":       "#C98A0A",
    "text":          "#161A22",
    "text_dim":      "#566073",
    "text_faint":    "#8A93A6",
}


def palette(mode: str = "dark") -> dict:
    return DARK if mode.lower() == "dark" else LIGHT


STATUS_ICON = {
    "online": "\U0001F7E2",   # 🟢
    "offline": "\U0001F534",  # 🔴
    "cached": "\U0001F7E1",   # 🟡
    "pegged": "\U0001F4CC",   # 📌
}

STATUS_TEXT = {
    "online": "Online",
    "offline": "Offline",
    "cached": "Cached Data",
    "pegged": "Pegged Rate",
}

TIME_RANGES = {
    "7 Days": 7,
    "30 Days": 30,
    "90 Days": 90,
    "1 Year": 365,
}
