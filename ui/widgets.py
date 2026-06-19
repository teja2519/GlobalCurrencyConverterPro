"""
ui/widgets.py

Small, reusable CustomTkinter widgets shared across the main window:

  * SearchableCurrencyDropdown — a button that opens a filterable popup
    list of currencies (bonus: "currency search inside dropdowns").
  * StatusBadge — the 🟢/🔴/🟡/📌 online/offline/cached/pegged indicator.
  * ResultCard — the big conversion-result display, with copy + save-as-image.
"""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from utils.constants import STATUS_ICON, STATUS_TEXT, palette
from utils.currencies import CURRENCIES, currency_label, flag_of, symbol_of
from utils.formatters import format_amount


class SearchableCurrencyDropdown(ctk.CTkFrame):
    """A button showing the current currency; click opens a searchable list."""

    def __init__(self, master, theme_mode: str, initial_code: str,
                 on_select: Callable[[str], None], **kwargs):
        colors = palette(theme_mode)
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme_mode = theme_mode
        self.code = initial_code
        self.on_select = on_select
        self._popup: Optional[ctk.CTkToplevel] = None

        self.button = ctk.CTkButton(
            self, text=currency_label(self.code), anchor="w",
            fg_color=colors["surface_alt"], hover_color=colors["accent_soft"],
            text_color=colors["text"], corner_radius=10, height=42, width=236,
            command=self._open_popup,
        )
        # CTkButton is a tkinter.Frame under the hood and never disables grid
        # propagation, so its internal text label silently grows the whole
        # button to fit long currency names (e.g. "New Zealand Dollar") and
        # shrinks it back for short ones (e.g. "USD"). Locking propagation
        # off keeps both dropdowns — and anything anchored next to them,
        # like the swap button — at a fixed, stable width regardless of
        # which currency is selected.
        self.button.grid_propagate(False)
        self.button.pack(fill="x")

    def set_theme(self, theme_mode: str) -> None:
        self.theme_mode = theme_mode
        colors = palette(theme_mode)
        self.button.configure(fg_color=colors["surface_alt"], hover_color=colors["accent_soft"],
                               text_color=colors["text"])

    def set_code(self, code: str) -> None:
        self.code = code
        self.button.configure(text=currency_label(code))

    def _open_popup(self) -> None:
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.lift()
            return

        colors = palette(self.theme_mode)
        popup = ctk.CTkToplevel(self)
        popup.title("Select currency")
        popup.geometry("360x420")
        popup.attributes("-topmost", True)
        popup.configure(fg_color=colors["bg"])
        self._popup = popup

        search_var = ctk.StringVar()
        entry = ctk.CTkEntry(popup, placeholder_text="Search currency or code\u2026",
                              textvariable=search_var, height=38, corner_radius=10)
        entry.pack(fill="x", padx=12, pady=(12, 8))
        entry.focus()

        list_frame = ctk.CTkScrollableFrame(popup, fg_color=colors["surface"])
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        def render(filter_text: str = "") -> None:
            for child in list_frame.winfo_children():
                child.destroy()
            filter_text = filter_text.strip().lower()
            for code, info in CURRENCIES.items():
                haystack = f"{code} {info['name']}".lower()
                if filter_text and filter_text not in haystack:
                    continue
                row = ctk.CTkButton(
                    list_frame, text=currency_label(code), anchor="w", height=38,
                    fg_color=colors["accent_soft"] if code == self.code else "transparent",
                    hover_color=colors["accent_soft"], text_color=colors["text"],
                    corner_radius=8,
                    command=lambda c=code: pick(c),
                )
                row.pack(fill="x", pady=2)

        def pick(code: str) -> None:
            self.set_code(code)
            self.on_select(code)
            popup.destroy()
            self._popup = None

        search_var.trace_add("write", lambda *_: render(search_var.get()))
        render()


class StatusBadge(ctk.CTkFrame):
    """Shows 🟢 Online / 🔴 Offline / 🟡 Cached Data / 📌 Pegged Rate."""

    def __init__(self, master, theme_mode: str, **kwargs):
        colors = palette(theme_mode)
        super().__init__(master, fg_color="transparent", **kwargs)
        self.label = ctk.CTkLabel(self, text="", text_color=colors["text_dim"],
                                   font=ctk.CTkFont(size=12, weight="bold"))
        self.label.pack()
        self.set_status("offline")

    def set_status(self, status: str) -> None:
        icon = STATUS_ICON.get(status, "\u26AA")
        text = STATUS_TEXT.get(status, status.title())
        self.label.configure(text=f"{icon}  {text}")

    def set_theme(self, theme_mode: str) -> None:
        colors = palette(theme_mode)
        self.label.configure(text_color=colors["text_dim"])


class ResultCard(ctk.CTkFrame):
    """The large card showing the converted amount and rate breakdown."""

    def __init__(self, master, theme_mode: str, on_copy: Callable[[str], None],
                 on_save_image: Callable[[str], None], **kwargs):
        colors = palette(theme_mode)
        super().__init__(master, fg_color=colors["card"], corner_radius=16, **kwargs)
        self.theme_mode = theme_mode
        self.on_copy = on_copy
        self.on_save_image = on_save_image

        self.from_line = ctk.CTkLabel(self, text="\u2014", font=ctk.CTkFont(size=16),
                                       text_color=colors["text_dim"])
        self.from_line.pack(pady=(18, 2))

        self.to_line = ctk.CTkLabel(self, text="\u2014", font=ctk.CTkFont(size=30, weight="bold"),
                                     text_color=colors["text"])
        self.to_line.pack(pady=(2, 8))

        self.rate_line = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=13),
                                       text_color=colors["text_dim"])
        self.rate_line.pack(pady=(0, 14))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(0, 16))
        self.copy_btn = ctk.CTkButton(btn_row, text="\U0001F4CB Copy Result", width=150, height=32,
                                       corner_radius=10, fg_color=colors["surface_alt"],
                                       hover_color=colors["accent_soft"], text_color=colors["text"],
                                       command=self._copy)
        self.copy_btn.pack(side="left", padx=6)
        self.save_btn = ctk.CTkButton(btn_row, text="\U0001F5BC Save as Image", width=150, height=32,
                                       corner_radius=10, fg_color=colors["surface_alt"],
                                       hover_color=colors["accent_soft"], text_color=colors["text"],
                                       command=self._save)
        self.save_btn.pack(side="left", padx=6)

        self._last_text = ""

    def set_theme(self, theme_mode: str) -> None:
        self.theme_mode = theme_mode
        colors = palette(theme_mode)
        self.configure(fg_color=colors["card"])
        self.from_line.configure(text_color=colors["text_dim"])
        self.to_line.configure(text_color=colors["text"])
        self.rate_line.configure(text_color=colors["text_dim"])
        for btn in (self.copy_btn, self.save_btn):
            btn.configure(fg_color=colors["surface_alt"], hover_color=colors["accent_soft"],
                          text_color=colors["text"])

    def show_result(self, amount: float, from_code: str, to_code: str,
                     converted: float, rate: float, precision: int = 2) -> None:
        f_flag, t_flag = flag_of(from_code), flag_of(to_code)
        t_sym = symbol_of(to_code)

        self.from_line.configure(text=f"{f_flag}  {format_amount(amount, precision)} {from_code}")
        self.to_line.configure(text=f"{t_flag}  {t_sym}{format_amount(converted, precision)} {to_code}")
        self.rate_line.configure(text=f"Rate:  1 {from_code} = {rate:.6f} {to_code}")

        self._last_text = (
            f"{f_flag} {format_amount(amount, precision)} {from_code} = "
            f"{t_flag} {t_sym}{format_amount(converted, precision)} {to_code} "
            f"(Rate: 1 {from_code} = {rate:.6f} {to_code})"
        )

    def show_placeholder(self, text: str) -> None:
        self.from_line.configure(text="\u2014")
        self.to_line.configure(text=text)
        self.rate_line.configure(text="")
        self._last_text = ""

    def show_error(self, message: str) -> None:
        colors = palette(self.theme_mode)
        self.from_line.configure(text="\u26A0  Couldn't convert")
        self.to_line.configure(text=message, text_color=colors["danger"])
        self.rate_line.configure(text="")
        self._last_text = ""

    def _copy(self) -> None:
        self.on_copy(self._last_text)

    def _save(self) -> None:
        self.on_save_image(self._last_text)
