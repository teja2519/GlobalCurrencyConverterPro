"""
ui/popups.py

Two bonus-feature popups that live outside the main window flow:

  * CalculatorKeypad  — an on-screen numeric keypad that types into the
    amount field (bonus #4: "Currency calculator keypad").
  * MiniFloatingWidget — a small always-on-top window showing one live
    converted amount, independent of the main window (bonus #10).
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from utils.constants import palette
from utils.currencies import currency_label, flag_of, symbol_of
from utils.formatters import format_amount


class CalculatorKeypad(ctk.CTkToplevel):
    """A simple on-screen keypad that appends digits into the amount entry."""

    KEYS = ["7", "8", "9", "4", "5", "6", "1", "2", "3", ".", "0", "\u232B"]

    def __init__(self, master, theme_mode: str, amount_var: ctk.StringVar):
        super().__init__(master)
        self.amount_var = amount_var
        colors = palette(theme_mode)
        self.title("Calculator")
        self.geometry("260x340")
        self.attributes("-topmost", True)
        self.configure(fg_color=colors["bg"])

        display = ctk.CTkLabel(self, textvariable=amount_var, font=ctk.CTkFont(size=22, weight="bold"),
                                text_color=colors["text"], height=50, anchor="e")
        display.pack(fill="x", padx=14, pady=(14, 8))

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        for i in range(4):
            grid.grid_rowconfigure(i, weight=1)
        for j in range(3):
            grid.grid_columnconfigure(j, weight=1)

        for idx, key in enumerate(self.KEYS):
            r, c = divmod(idx, 3)
            btn = ctk.CTkButton(
                grid, text=key, corner_radius=10, fg_color=colors["surface_alt"],
                hover_color=colors["accent_soft"], text_color=colors["text"],
                font=ctk.CTkFont(size=16),
                command=lambda k=key: self._press(k),
            )
            btn.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)

        clear_btn = ctk.CTkButton(self, text="Clear", corner_radius=10, fg_color=colors["danger"],
                                   hover_color=colors["danger"], command=self._clear)
        clear_btn.pack(fill="x", padx=14, pady=(0, 14))

    def _press(self, key: str) -> None:
        current = self.amount_var.get()
        if key == "\u232B":
            self.amount_var.set(current[:-1])
        elif key == "." and "." in current:
            return
        else:
            self.amount_var.set(current + key)

    def _clear(self) -> None:
        self.amount_var.set("")


class MiniFloatingWidget(ctk.CTkToplevel):
    """A tiny always-on-top widget showing one live currency pair."""

    def __init__(self, master, theme_mode: str, from_code: str, to_code: str,
                 get_rate: Callable[[str, str], float]):
        super().__init__(master)
        self.get_rate = get_rate
        self.from_code = from_code
        self.to_code = to_code
        colors = palette(theme_mode)

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry("220x90+80+80")
        self.configure(fg_color=colors["card"])

        bar = ctk.CTkFrame(self, fg_color=colors["surface_alt"], height=22, corner_radius=0)
        bar.pack(fill="x")
        bar.bind("<Button-1>", self._start_move)
        bar.bind("<B1-Motion>", self._do_move)

        close_btn = ctk.CTkButton(bar, text="\u2715", width=22, height=18, corner_radius=6,
                                   fg_color="transparent", hover_color=colors["danger"],
                                   text_color=colors["text_dim"], command=self.destroy)
        close_btn.pack(side="right", padx=2, pady=2)

        self.pair_label = ctk.CTkLabel(
            self, text=f"{flag_of(from_code)} {from_code} \u2192 {flag_of(to_code)} {to_code}",
            font=ctk.CTkFont(size=12), text_color=colors["text_dim"])
        self.pair_label.pack(pady=(8, 0))

        self.rate_label = ctk.CTkLabel(self, text="\u2014", font=ctk.CTkFont(size=18, weight="bold"),
                                        text_color=colors["text"])
        self.rate_label.pack(pady=(2, 8))

        self._refresh()

    def _refresh(self) -> None:
        rate = self.get_rate(self.from_code, self.to_code)
        if rate:
            self.rate_label.configure(
                text=f"1 = {symbol_of(self.to_code)}{format_amount(rate, 4)}"
            )
        if self.winfo_exists():
            self.after(60_000, self._refresh)

    def _start_move(self, event) -> None:
        self._drag_x, self._drag_y = event.x, event.y

    def _do_move(self, event) -> None:
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")
