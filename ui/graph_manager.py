"""
ui/graph_manager.py

GraphManager embeds a Matplotlib line chart inside a CustomTkinter frame to
visualise historical exchange-rate movement for the selected currency pair,
across the four required time ranges.
"""

from __future__ import annotations

import threading
import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from utils.constants import TIME_RANGES, palette


class GraphManager:
    """Owns the chart canvas and (re)draws it from historical rate data."""

    def __init__(self, parent: ctk.CTkBaseClass, theme_mode: str,
                 on_fetch_series: Callable[[str, str, int], dict]):
        """
        parent:          the CTk container to build inside.
        on_fetch_series: callable(from_code, to_code, days) -> {date: rate}
                          (kept generic so GraphManager has zero knowledge
                          of the network layer — easier to test/reuse).
        """
        self.parent = parent
        self.theme_mode = theme_mode
        self.on_fetch_series = on_fetch_series
        self.current_range_label = "30 Days"
        self.current_from = "USD"
        self.current_to = "INR"
        self._build()

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        colors = palette(self.theme_mode)
        self.frame = ctk.CTkFrame(self.parent, fg_color=colors["card"], corner_radius=14)

        controls = ctk.CTkFrame(self.frame, fg_color="transparent")
        controls.pack(fill="x", padx=14, pady=(14, 6))

        self.range_buttons = {}
        for label in TIME_RANGES:
            btn = ctk.CTkButton(
                controls, text=label, width=86, height=30, corner_radius=10,
                fg_color=colors["accent"] if label == self.current_range_label else colors["surface_alt"],
                hover_color=colors["accent_hover"],
                text_color="#FFFFFF" if label == self.current_range_label else colors["text_dim"],
                command=lambda l=label: self.set_range(l),
            )
            btn.pack(side="left", padx=4)
            self.range_buttons[label] = btn

        self.loading_label = ctk.CTkLabel(controls, text="", text_color=colors["text_faint"])
        self.loading_label.pack(side="right", padx=6)

        self.figure = Figure(figsize=(5.6, 2.7), dpi=100)
        self.figure.patch.set_facecolor(colors["card"])
        self.ax = self.figure.add_subplot(111)
        self._style_axes(colors)

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _style_axes(self, colors: dict) -> None:
        self.ax.clear()
        self.ax.set_facecolor(colors["card"])
        for spine in self.ax.spines.values():
            spine.set_color(colors["border"])
        self.ax.tick_params(colors=colors["text_dim"], labelsize=8)
        self.ax.grid(True, color=colors["border"], linewidth=0.6, alpha=0.6)

    # --------------------------------------------------------------- logic
    def set_pair(self, from_code: str, to_code: str) -> None:
        self.current_from, self.current_to = from_code, to_code
        self.refresh()

    def set_range(self, label: str) -> None:
        self.current_range_label = label
        colors = palette(self.theme_mode)
        for lbl, btn in self.range_buttons.items():
            active = lbl == label
            btn.configure(
                fg_color=colors["accent"] if active else colors["surface_alt"],
                text_color="#FFFFFF" if active else colors["text_dim"],
            )
        self.refresh()

    def set_theme(self, theme_mode: str) -> None:
        self.theme_mode = theme_mode
        colors = palette(theme_mode)
        self.frame.configure(fg_color=colors["card"])
        self.figure.patch.set_facecolor(colors["card"])
        self._style_axes(colors)
        self.canvas.draw_idle()

    def refresh(self) -> None:
        """Fetch the series in a background thread, then redraw on the UI thread."""
        days = TIME_RANGES[self.current_range_label]
        from_code, to_code = self.current_from, self.current_to
        self.loading_label.configure(text="Loading chart\u2026")

        def worker():
            series = self.on_fetch_series(from_code, to_code, days)
            self._schedule_draw(series, from_code, to_code)

        threading.Thread(target=worker, daemon=True).start()

    def _schedule_draw(self, series: dict, from_code: str, to_code: str) -> None:
        # A theme switch rebuilds the Graph tab from scratch, which destroys
        # this exact GraphManager's frame/canvas. If a fetch that started
        # before the switch finishes afterward, this instance is stale —
        # skip silently instead of throwing into a dead widget.
        try:
            if self.frame.winfo_exists():
                self.frame.after(0, lambda: self._draw(series, from_code, to_code))
        except (RuntimeError, tk.TclError):
            pass

    def _draw(self, series: dict, from_code: str, to_code: str) -> None:
        try:
            if not self.frame.winfo_exists():
                return
        except tk.TclError:
            return

        colors = palette(self.theme_mode)
        self._style_axes(colors)
        self.loading_label.configure(text="")

        if not series:
            self.ax.text(0.5, 0.5, "No historical data available\n(check your connection)",
                          ha="center", va="center", color=colors["text_faint"], fontsize=9,
                          transform=self.ax.transAxes)
            self.canvas.draw_idle()
            return

        dates = list(series.keys())
        values = list(series.values())
        self.ax.plot(dates, values, color=colors["accent"], linewidth=2)
        self.ax.fill_between(range(len(dates)), values, min(values), color=colors["accent"], alpha=0.08)

        step = max(1, len(dates) // 6)
        self.ax.set_xticks(range(0, len(dates), step))
        self.ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=20, ha="right")
        self.ax.set_title(f"{from_code} \u2192 {to_code}", color=colors["text"], fontsize=10, loc="left")
        self.figure.tight_layout()
        self.canvas.draw_idle()
