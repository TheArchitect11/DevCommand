"""Custom Textual themes for DevCommand."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Theme colour palettes — Textual CSS variables
# ---------------------------------------------------------------------------

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "background": "#0d1117",
        "surface": "#161b22",
        "primary": "#58a6ff",
        "secondary": "#8b949e",
        "accent": "#f78166",
        "success": "#3fb950",
        "warning": "#d29922",
        "error": "#f85149",
        "text": "#c9d1d9",
        "text-muted": "#8b949e",
    },
    "light": {
        "background": "#ffffff",
        "surface": "#f6f8fa",
        "primary": "#0969da",
        "secondary": "#57606a",
        "accent": "#cf222e",
        "success": "#1a7f37",
        "warning": "#9a6700",
        "error": "#cf222e",
        "text": "#24292f",
        "text-muted": "#57606a",
    },
    "nord": {
        "background": "#2e3440",
        "surface": "#3b4252",
        "primary": "#88c0d0",
        "secondary": "#81a1c1",
        "accent": "#bf616a",
        "success": "#a3be8c",
        "warning": "#ebcb8b",
        "error": "#bf616a",
        "text": "#eceff4",
        "text-muted": "#d8dee9",
    },
    "dracula": {
        "background": "#282a36",
        "surface": "#44475a",
        "primary": "#bd93f9",
        "secondary": "#6272a4",
        "accent": "#ff79c6",
        "success": "#50fa7b",
        "warning": "#f1fa8c",
        "error": "#ff5555",
        "text": "#f8f8f2",
        "text-muted": "#6272a4",
    },
    "solarized": {
        "background": "#002b36",
        "surface": "#073642",
        "primary": "#268bd2",
        "secondary": "#2aa198",
        "accent": "#cb4b16",
        "success": "#859900",
        "warning": "#b58900",
        "error": "#dc322f",
        "text": "#839496",
        "text-muted": "#586e75",
    },
}


def get_theme(name: str) -> dict[str, str]:
    """Return a theme palette by name, falling back to 'dark'."""
    return THEMES.get(name, THEMES["dark"])


def available_themes() -> list[str]:
    """Return list of available theme names."""
    return list(THEMES.keys())
