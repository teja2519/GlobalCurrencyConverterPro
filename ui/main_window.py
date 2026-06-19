"""
ui/main_window.py
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import customtkinter as ctk

from api.converter_engine import ConverterEngine
from data.alerts_manager import AlertsManager
from data.favorites_manager import FavoritesManager
from data.history_manager import HistoryManager
from data.settings_manager import SettingsManager
from ui.graph_manager import GraphManager
from ui.popups import CalculatorKeypad, MiniFloatingWidget
from ui.widgets import ResultCard, SearchableCurrencyDropdown, StatusBadge
from utils.constants import APP_NAME, MIN_HEIGHT, MIN_WIDTH, palette
from utils.currencies import CURRENCIES, short_label
from utils.formatters import format_amount
from utils.i18n import LANGUAGES, t


ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings = SettingsManager()
        self.engine   = ConverterEngine()
        self.history  = HistoryManager()
        self.favorites = FavoritesManager()
        self.alerts   = AlertsManager()

        self.theme_mode = self.settings.get("theme")
        self.language   = self.settings.get("language")
        ctk.set_appearance_mode(self.theme_mode)
        ctk.set_default_color_theme("blue")

        self.from_code = self.settings.get("default_from")
        self.to_code   = self.settings.get("default_to")
        self._mini_widget: Optional[MiniFloatingWidget] = None
        self._auto_refresh_job = None

        self.title(APP_NAME)
        self.geometry(f"{MIN_WIDTH}x{MIN_HEIGHT}")
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self._set_icon()

        colors = palette(self.theme_mode)
        self.configure(fg_color=colors["bg"])

        self._build_layout()
        self._wire_ttk_style()
        self._refresh_history_table()
        self._schedule_auto_refresh()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ icon
    def _set_icon(self) -> None:
        ico = os.path.join(ASSETS_DIR, "icon.ico")
        png = os.path.join(ASSETS_DIR, "icon.png")
        try:
            if os.name == "nt" and os.path.exists(ico):
                self.iconbitmap(ico)
            elif os.path.exists(png):
                img = tk.PhotoImage(file=png)
                self.iconphoto(True, img)
                self._icon_ref = img          # keep alive
        except Exception:
            pass

    # ---------------------------------------------------------------- layout
    def _build_layout(self) -> None:
        colors = palette(self.theme_mode)
        self._build_header()

        self.tabview = ctk.CTkTabview(
            self, corner_radius=14,
            fg_color=colors["surface"],
            segmented_button_fg_color=colors["surface_alt"],
            segmented_button_selected_color=colors["accent"],
            segmented_button_selected_hover_color=colors["accent_hover"],
            segmented_button_unselected_color=colors["surface_alt"],
            segmented_button_unselected_hover_color=colors["accent_soft"],
            text_color=colors["text"],
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        self.tab_converter = self.tabview.add("Converter")
        self.tab_history   = self.tabview.add("History")
        self.tab_graph     = self.tabview.add("Graph")
        self.tab_settings  = self.tabview.add("Settings")

        self._build_converter_tab(self.tab_converter)
        self._build_history_tab(self.tab_history)
        self._build_graph_tab(self.tab_graph)
        self._build_settings_tab(self.tab_settings)

    # ---------------------------------------------------------------- header
    def _build_header(self) -> None:
        colors = palette(self.theme_mode)
        header = ctk.CTkFrame(self, fg_color=colors["surface"], corner_radius=0, height=84)
        header.pack(fill="x")

        text_col = ctk.CTkFrame(header, fg_color="transparent")
        text_col.pack(side="left", padx=20, pady=12)
        self.title_label = ctk.CTkLabel(
            text_col, text=f"\U0001F4B1  {t('title', self.language)}",
            font=ctk.CTkFont(size=20, weight="bold"), text_color=colors["text"], anchor="w")
        self.title_label.pack(anchor="w")
        self.subtitle_label = ctk.CTkLabel(
            text_col, text=t("subtitle", self.language),
            font=ctk.CTkFont(size=12), text_color=colors["text_dim"], anchor="w")
        self.subtitle_label.pack(anchor="w")

        tools = ctk.CTkFrame(header, fg_color="transparent")
        tools.pack(side="right", padx=20, pady=12)

        # Use universally-supported emoji glyphs so they show on all platforms
        self.keypad_btn = ctk.CTkButton(
            tools, text="\U0001F522", width=42, height=42, corner_radius=10,
            fg_color=colors["surface_alt"], hover_color=colors["accent_soft"],
            text_color=colors["text"], command=self._open_keypad)
        self.keypad_btn.pack(side="left", padx=4)

        self.mini_btn = ctk.CTkButton(
            tools, text="\U0001F4CC", width=42, height=42, corner_radius=10,
            fg_color=colors["surface_alt"], hover_color=colors["accent_soft"],
            text_color=colors["text"], command=self._open_mini_widget)
        self.mini_btn.pack(side="left", padx=4)
        self.header_frame = header

    # ============================================================ CONVERTER
    def _build_converter_tab(self, parent) -> None:
        colors = palette(self.theme_mode)
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self.converter_scroll = scroll

        # amount
        amount_card = ctk.CTkFrame(scroll, fg_color=colors["card"], corner_radius=14)
        amount_card.pack(fill="x", pady=(4, 12))
        ctk.CTkLabel(amount_card, text=t("amount", self.language), anchor="w",
                     text_color=colors["text_dim"],
                     font=ctk.CTkFont(size=12)).pack(fill="x", padx=16, pady=(12, 2))

        self.amount_var = ctk.StringVar(value="100")
        self.amount_entry = ctk.CTkEntry(
            amount_card, textvariable=self.amount_var,
            placeholder_text=t("amount", self.language),
            height=46, corner_radius=10, font=ctk.CTkFont(size=18),
            text_color=colors["text"])
        self.amount_entry.pack(fill="x", padx=16, pady=(0, 6))
        self.amount_entry.bind("<Return>", lambda e: self.perform_conversion())

        self.amount_error = ctk.CTkLabel(
            amount_card, text="", text_color=colors["danger"],
            font=ctk.CTkFont(size=11), anchor="w")
        self.amount_error.pack(fill="x", padx=16, pady=(0, 12))

        # --- currency selector card -----------------------------------------
        # Uses a 3-column grid: [From col] [Swap btn] [To col]
        # The swap button sits in column=1 with a FIXED width. The two
        # dropdown columns each have weight=1 so they always share remaining
        # space equally. Because SearchableCurrencyDropdown.button now has
        # grid_propagate(False) the columns never grow to fit label text,
        # which would otherwise shift the swap button sideways.
        select_card = ctk.CTkFrame(scroll, fg_color=colors["card"], corner_radius=14)
        select_card.pack(fill="x", pady=(0, 12))
        select_card.grid_columnconfigure(0, weight=1, uniform="col")
        select_card.grid_columnconfigure(1, weight=0, minsize=58)   # fixed swap-btn column
        select_card.grid_columnconfigure(2, weight=1, uniform="col")

        from_col = ctk.CTkFrame(select_card, fg_color="transparent")
        from_col.grid(row=0, column=0, sticky="nsew", padx=(16, 4), pady=16)
        ctk.CTkLabel(from_col, text=t("from", self.language),
                     text_color=colors["text_dim"],
                     font=ctk.CTkFont(size=12), anchor="w").pack(fill="x", pady=(0, 6))
        self.from_dropdown = SearchableCurrencyDropdown(
            from_col, self.theme_mode, self.from_code, self._on_from_change)
        self.from_dropdown.pack(fill="x")

        # Swap button in its own fixed column — never moves regardless of label length
        self.swap_btn = ctk.CTkButton(
            select_card, text="\u21C6", width=42, height=42, corner_radius=21,
            fg_color=colors["accent"], hover_color=colors["accent_hover"],
            text_color="#FFFFFF", font=ctk.CTkFont(size=18, weight="bold"),
            command=self._on_swap)
        self.swap_btn.grid(row=0, column=1, padx=6, pady=16)

        to_col = ctk.CTkFrame(select_card, fg_color="transparent")
        to_col.grid(row=0, column=2, sticky="nsew", padx=(4, 16), pady=16)
        ctk.CTkLabel(to_col, text=t("to", self.language),
                     text_color=colors["text_dim"],
                     font=ctk.CTkFont(size=12), anchor="w").pack(fill="x", pady=(0, 6))
        self.to_dropdown = SearchableCurrencyDropdown(
            to_col, self.theme_mode, self.to_code, self._on_to_change)
        self.to_dropdown.pack(fill="x")

        # fav + convert
        action_row = ctk.CTkFrame(scroll, fg_color="transparent")
        action_row.pack(fill="x", pady=(0, 12))
        self.fav_btn = ctk.CTkButton(
            action_row, text="\u2606", width=46, height=50, corner_radius=12,
            fg_color=colors["surface_alt"], hover_color=colors["accent_soft"],
            text_color=colors["warning"], font=ctk.CTkFont(size=18),
            command=self._toggle_favorite)
        self.fav_btn.pack(side="left", padx=(0, 8))
        self.convert_btn = ctk.CTkButton(
            action_row, text=t("convert", self.language), height=50, corner_radius=12,
            fg_color=colors["accent"], hover_color=colors["accent_hover"],
            text_color="#FFFFFF", font=ctk.CTkFont(size=16, weight="bold"),
            command=self.perform_conversion)
        self.convert_btn.pack(side="left", fill="x", expand=True)
        self._update_fav_button()

        # result card
        self.result_card = ResultCard(
            scroll, self.theme_mode, self._copy_result, self._save_result_image)
        self.result_card.pack(fill="x", pady=(0, 12))
        self.result_card.show_placeholder("Enter an amount and tap Convert")

        # status bar
        info_card = ctk.CTkFrame(scroll, fg_color=colors["card"], corner_radius=14)
        info_card.pack(fill="x", pady=(0, 12))
        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(fill="x", padx=16, pady=12)
        self.status_badge = StatusBadge(info_inner, self.theme_mode)
        self.status_badge.pack(side="left")
        self.updated_label = ctk.CTkLabel(
            info_inner, text=f"{t('last_updated', self.language)}: \u2014",
            text_color=colors["text_faint"], font=ctk.CTkFont(size=11))
        self.updated_label.pack(side="right")

        # favorites quick-access
        fav_card = ctk.CTkFrame(scroll, fg_color=colors["card"], corner_radius=14)
        fav_card.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(fav_card, text=f"\u2B50 {t('favorites', self.language)}",
                     anchor="w", text_color=colors["text"],
                     font=ctk.CTkFont(size=13, weight="bold")).pack(
            fill="x", padx=16, pady=(12, 6))
        self.favorites_row = ctk.CTkFrame(fav_card, fg_color="transparent")
        self.favorites_row.pack(fill="x", padx=12, pady=(0, 12))
        self._refresh_favorites_row()

    # -------------------------------------------------------- converter logic
    def _on_from_change(self, code: str) -> None:
        self.from_code = code
        self._update_fav_button()

    def _on_to_change(self, code: str) -> None:
        self.to_code = code
        self._update_fav_button()

    def _on_swap(self) -> None:
        self.from_code, self.to_code = self.to_code, self.from_code
        self.from_dropdown.set_code(self.from_code)
        self.to_dropdown.set_code(self.to_code)
        self._update_fav_button()

    def _toggle_favorite(self) -> None:
        self.favorites.toggle(self.from_code, self.to_code)
        self._update_fav_button()
        self._refresh_favorites_row()

    def _update_fav_button(self) -> None:
        colors = palette(self.theme_mode)
        is_fav = self.favorites.is_favorite(self.from_code, self.to_code)
        self.fav_btn.configure(
            text="\u2605" if is_fav else "\u2606",
            text_color=colors["warning"] if is_fav else colors["text_dim"])

    def _refresh_favorites_row(self) -> None:
        for child in self.favorites_row.winfo_children():
            child.destroy()
        colors = palette(self.theme_mode)
        pairs = self.favorites.list_pairs()
        if not pairs:
            ctk.CTkLabel(self.favorites_row,
                         text="No favorites yet \u2014 tap \u2606 above to add one.",
                         text_color=colors["text_faint"],
                         font=ctk.CTkFont(size=11)).pack(anchor="w")
            return
        for f_code, t_code in pairs:
            label = f"\u2B50 {short_label(f_code)} \u2192 {short_label(t_code)}"
            btn = ctk.CTkButton(
                self.favorites_row, text=label, height=32, corner_radius=10,
                fg_color=colors["surface_alt"], hover_color=colors["accent_soft"],
                text_color=colors["text"], font=ctk.CTkFont(size=11),
                command=lambda fc=f_code, tc=t_code: self._apply_pair(fc, tc))
            btn.pack(side="left", padx=4, pady=2)

    def _apply_pair(self, from_code: str, to_code: str) -> None:
        self.from_code, self.to_code = from_code, to_code
        self.from_dropdown.set_code(from_code)
        self.to_dropdown.set_code(to_code)
        self._update_fav_button()
        self.perform_conversion()

    def perform_conversion(self) -> None:
        self.amount_error.configure(text="")
        raw  = self.amount_var.get()
        fc, tc = self.from_code, self.to_code
        self.convert_btn.configure(state="disabled", text="Converting\u2026")

        def worker():
            result = self.engine.convert(raw, fc, tc)
            self.after(0, lambda: self._on_conversion_done(result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_conversion_done(self, result) -> None:
        self.convert_btn.configure(state="normal", text=t("convert", self.language))
        if not result.ok:
            lowered = result.error.lower()
            if any(k in lowered for k in ("amount", "zero", "number", "large", "enter")):
                self.amount_error.configure(text=result.error)
            else:
                self.result_card.show_error(result.error)
            return

        precision = int(self.settings.get("decimal_precision"))
        self.result_card.show_result(
            result.amount, result.from_code, result.to_code,
            result.converted, result.rate, precision)
        self.status_badge.set_status(result.status)
        self.updated_label.configure(
            text=f"{t('last_updated', self.language)}: "
                 f"{result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        self.history.add_entry(
            result.from_code, result.to_code,
            result.amount, result.converted, result.rate, result.timestamp)
        self._refresh_history_table()

        fired = self.alerts.check(result.from_code, result.to_code, result.rate)
        for alert in fired:
            messagebox.showinfo("Exchange Rate Alert", f"Alert triggered: {alert.label()}")
        if fired and hasattr(self, "alerts_list_frame"):
            self._refresh_alerts_list()

    # ----------------------------------------------------------- copy / save
    def _copy_result(self, text: str) -> None:
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def _save_result_image(self, text: str) -> None:
        if not text:
            messagebox.showwarning("Nothing to save", "Convert an amount first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG image", "*.png")],
            initialfile="conversion_result.png")
        if not path:
            return
        try:
            from PIL import Image, ImageDraw, ImageFont
            colors = palette(self.theme_mode)
            img  = Image.new("RGB", (640, 220), colors["card"])
            draw = ImageDraw.Draw(img)
            try:
                font_b = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
                font_s = ImageFont.truetype("DejaVuSans.ttf", 14)
            except OSError:
                font_b = font_s = ImageFont.load_default()
            draw.text((24, 24),  APP_NAME, fill=colors["text_dim"], font=font_s)
            draw.text((24, 70),  text,     fill=colors["text"],     font=font_b)
            draw.text((24, 180), "Generated by Global Currency Converter Pro",
                      fill=colors["text_faint"], font=font_s)
            img.save(path)
            messagebox.showinfo("Saved", f"Result card saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Couldn't save image", str(exc))

    # ----------------------------------------------------------- popups
    def _open_keypad(self) -> None:
        CalculatorKeypad(self, self.theme_mode, self.amount_var)

    def _open_mini_widget(self) -> None:
        if self._mini_widget and self._mini_widget.winfo_exists():
            self._mini_widget.lift()
            return
        def get_rate(fc, tc):
            rate, _s, _t = self.engine.get_rate_only(fc, tc)
            return rate
        self._mini_widget = MiniFloatingWidget(
            self, self.theme_mode, self.from_code, self.to_code, get_rate)

    # ============================================================ HISTORY
    def _build_history_tab(self, parent) -> None:
        colors = palette(self.theme_mode)
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="both", expand=True)

        # toolbar
        toolbar = ctk.CTkFrame(container, fg_color="transparent")
        toolbar.pack(fill="x", pady=(4, 8))

        self.history_search_var = ctk.StringVar()
        ctk.CTkEntry(
            toolbar, textvariable=self.history_search_var,
            placeholder_text=t("search", self.language),
            text_color=colors["text"], height=36, corner_radius=10
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.history_search_var.trace_add("write", lambda *_: self._refresh_history_table())

        ctk.CTkButton(
            toolbar, text=t("delete_selected", self.language), height=36, width=130,
            corner_radius=10, fg_color=colors["surface_alt"],
            hover_color=colors["danger"], text_color=colors["text"],
            command=self._delete_selected_history).pack(side="left", padx=4)
        ctk.CTkButton(
            toolbar, text=t("clear_history", self.language), height=36, width=120,
            corner_radius=10, fg_color=colors["danger"], hover_color=colors["danger"],
            text_color="#FFFFFF", command=self._clear_history).pack(side="left", padx=4)

        export_row = ctk.CTkFrame(container, fg_color="transparent")
        export_row.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(
            export_row, text=t("export_csv", self.language), height=34, corner_radius=10,
            fg_color=colors["surface_alt"], hover_color=colors["accent_soft"],
            text_color=colors["text"],
            command=self._export_history_csv).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            export_row, text=t("export_pdf", self.language), height=34, corner_radius=10,
            fg_color=colors["surface_alt"], hover_color=colors["accent_soft"],
            text_color=colors["text"],
            command=self._export_history_pdf).pack(side="left")

        # table
        table_holder = ctk.CTkFrame(container, fg_color=colors["card"], corner_radius=12)
        table_holder.pack(fill="both", expand=True, pady=(0, 4))
        cols = ["Date", "Time", "From", "To", "Original Amount", "Converted Amount", "Rate"]
        self.history_tree = ttk.Treeview(
            table_holder, columns=cols, show="headings", height=12)
        for col in cols:
            self.history_tree.heading(
                col, text=col, command=lambda c=col: self._sort_history(c))
            self.history_tree.column(col, width=90, anchor="center")
        self.history_tree.pack(fill="both", expand=True, padx=8, pady=8)
        self._history_sort_state = {"column": None, "ascending": True}

    def _sort_history(self, column: str) -> None:
        s = self._history_sort_state
        asc = not s["ascending"] if s["column"] == column else True
        self._history_sort_state = {"column": column, "ascending": asc}
        self._refresh_history_table()

    def _refresh_history_table(self) -> None:
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        query = self.history_search_var.get() if hasattr(self, "history_search_var") else ""
        df = self.history.search(query)
        s = self._history_sort_state if hasattr(self, "_history_sort_state") else {"column": None}
        if s.get("column"):
            df = df.sort_values(by=s["column"], ascending=s["ascending"])
        for idx, row in df.iterrows():
            self.history_tree.insert("", "end", iid=str(idx), values=list(row))

    def _delete_selected_history(self) -> None:
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showinfo("Nothing selected", "Select one or more rows to delete.")
            return
        for idx in sorted((int(s) for s in selected), reverse=True):
            self.history.delete_entry(idx)
        self._refresh_history_table()

    def _clear_history(self) -> None:
        if messagebox.askyesno("Clear history",
                               "Permanently delete all conversion history?"):
            self.history.clear_history()
            self._refresh_history_table()

    def _export_history_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV file", "*.csv")],
            initialfile="conversion_history.csv")
        if path:
            self.history.export_csv(path)
            messagebox.showinfo("Exported", f"History exported to:\n{path}")

    def _export_history_pdf(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF file", "*.pdf")],
            initialfile="conversion_history.pdf")
        if path:
            try:
                self.history.export_pdf(path)
                messagebox.showinfo("Exported", f"Report exported to:\n{path}")
            except Exception as exc:
                messagebox.showerror("Export failed", str(exc))

    # ============================================================ GRAPH
    def _build_graph_tab(self, parent) -> None:
        colors = palette(self.theme_mode)
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="both", expand=True)

        ctk.CTkLabel(container, text=t("graph", self.language),
                     text_color=colors["text"],
                     font=ctk.CTkFont(size=15, weight="bold"),
                     anchor="w").pack(fill="x", pady=(2, 8))

        pair_row = ctk.CTkFrame(container, fg_color="transparent")
        pair_row.pack(fill="x", pady=(0, 10))

        from_col = ctk.CTkFrame(pair_row, fg_color="transparent")
        from_col.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(from_col, text=t("from", self.language),
                     text_color=colors["text_dim"],
                     font=ctk.CTkFont(size=11), anchor="w").pack(fill="x")
        self.graph_from_dropdown = SearchableCurrencyDropdown(
            from_col, self.theme_mode, self.from_code, self._on_graph_pair_change)
        self.graph_from_dropdown.pack(fill="x")

        to_col = ctk.CTkFrame(pair_row, fg_color="transparent")
        to_col.pack(side="left", fill="x", expand=True, padx=(6, 0))
        ctk.CTkLabel(to_col, text=t("to", self.language),
                     text_color=colors["text_dim"],
                     font=ctk.CTkFont(size=11), anchor="w").pack(fill="x")
        self.graph_to_dropdown = SearchableCurrencyDropdown(
            to_col, self.theme_mode, self.to_code, self._on_graph_pair_change)
        self.graph_to_dropdown.pack(fill="x")

        self.graph_manager = GraphManager(container, self.theme_mode, self._fetch_series)
        self.graph_manager.frame.pack(fill="both", expand=True)
        self.graph_manager.set_pair(self.from_code, self.to_code)

    def _on_graph_pair_change(self, _code: str) -> None:
        self.graph_manager.set_pair(
            self.graph_from_dropdown.code, self.graph_to_dropdown.code)

    def _fetch_series(self, from_code: str, to_code: str, days: int) -> dict:
        return self.engine.api.get_historical_series(from_code, to_code, days)

    # ============================================================ SETTINGS
    def _build_settings_tab(self, parent) -> None:
        colors = palette(self.theme_mode)
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # --- theme toggle ---------------------------------------------------
        theme_card = ctk.CTkFrame(scroll, fg_color=colors["card"], corner_radius=14)
        theme_card.pack(fill="x", pady=(4, 12))
        ctk.CTkLabel(theme_card, text=t("settings", self.language),
                     text_color=colors["text"],
                     font=ctk.CTkFont(size=14, weight="bold"),
                     anchor="w").pack(fill="x", padx=16, pady=(14, 10))

        # CTkSegmentedButton needs explicit text_color for light mode;
        # the library default is near-white in both modes.
        theme_seg = ctk.CTkSegmentedButton(
            theme_card,
            values=[t("dark_mode", self.language), t("light_mode", self.language)],
            fg_color=colors["surface_alt"],
            selected_color=colors["accent"],
            selected_hover_color=colors["accent_hover"],
            unselected_color=colors["surface_alt"],
            unselected_hover_color=colors["accent_soft"],
            text_color=colors["text"],
            command=self._on_theme_switch)
        theme_seg.set(
            t("dark_mode", self.language) if self.theme_mode == "dark"
            else t("light_mode", self.language))
        theme_seg.pack(fill="x", padx=16, pady=(0, 16))

        # --- preferences ----------------------------------------------------
        pref_card = ctk.CTkFrame(scroll, fg_color=colors["card"], corner_radius=14)
        pref_card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(pref_card, text="Preferences",
                     text_color=colors["text"],
                     font=ctk.CTkFont(size=14, weight="bold"),
                     anchor="w").pack(fill="x", padx=16, pady=(14, 10))

        ctk.CTkLabel(pref_card, text=t("default_pair", self.language),
                     text_color=colors["text_dim"],
                     font=ctk.CTkFont(size=11), anchor="w").pack(fill="x", padx=16)
        pair_row = ctk.CTkFrame(pref_card, fg_color="transparent")
        pair_row.pack(fill="x", padx=16, pady=(4, 12))
        self.settings_from_var = ctk.StringVar(value=self.from_code)
        self.settings_to_var   = ctk.StringVar(value=self.to_code)

        # All CTkOptionMenus get explicit text_color + dropdown colours so
        # they're readable in both dark and light themes.
        om_kw = dict(
            fg_color=colors["surface_alt"], button_color=colors["accent"],
            button_hover_color=colors["accent_hover"], text_color=colors["text"],
            dropdown_fg_color=colors["surface"],
            dropdown_hover_color=colors["accent_soft"],
            dropdown_text_color=colors["text"])
        ctk.CTkOptionMenu(pair_row, values=list(CURRENCIES.keys()),
                          variable=self.settings_from_var, width=110, **om_kw).pack(side="left")
        ctk.CTkLabel(pair_row, text="\u2192",
                     text_color=colors["text_dim"]).pack(side="left", padx=8)
        ctk.CTkOptionMenu(pair_row, values=list(CURRENCIES.keys()),
                          variable=self.settings_to_var, width=110, **om_kw).pack(side="left")

        ctk.CTkLabel(pref_card, text=t("decimal_precision", self.language),
                     text_color=colors["text_dim"],
                     font=ctk.CTkFont(size=11), anchor="w").pack(fill="x", padx=16)
        self.precision_var = ctk.IntVar(value=int(self.settings.get("decimal_precision")))
        prec_row = ctk.CTkFrame(pref_card, fg_color="transparent")
        prec_row.pack(fill="x", padx=16, pady=(4, 12))
        prec_slider = ctk.CTkSlider(prec_row, from_=0, to=6, number_of_steps=6,
                                    variable=self.precision_var, width=200)
        prec_slider.pack(side="left")
        self.precision_lbl = ctk.CTkLabel(prec_row, text=str(self.precision_var.get()),
                                          text_color=colors["text"], width=24)
        self.precision_lbl.pack(side="left", padx=8)
        prec_slider.configure(
            command=lambda v: self.precision_lbl.configure(text=str(int(v))))

        ctk.CTkLabel(pref_card, text=t("auto_refresh", self.language),
                     text_color=colors["text_dim"],
                     font=ctk.CTkFont(size=11), anchor="w").pack(fill="x", padx=16)
        self.refresh_var = ctk.StringVar(
            value=str(self.settings.get("auto_refresh_seconds")))
        ctk.CTkEntry(pref_card, textvariable=self.refresh_var,
                     text_color=colors["text"], width=100, height=34,
                     corner_radius=8).pack(anchor="w", padx=16, pady=(4, 12))

        ctk.CTkLabel(pref_card, text=t("language", self.language),
                     text_color=colors["text_dim"],
                     font=ctk.CTkFont(size=11), anchor="w").pack(fill="x", padx=16)
        self.language_var = ctk.StringVar(value=self.language)
        ctk.CTkOptionMenu(pref_card, values=LANGUAGES,
                          variable=self.language_var, width=150,
                          **om_kw).pack(anchor="w", padx=16, pady=(4, 14))

        ctk.CTkButton(pref_card, text=t("save_settings", self.language),
                      height=40, corner_radius=10,
                      fg_color=colors["accent"], hover_color=colors["accent_hover"],
                      text_color="#FFFFFF",
                      command=self._save_settings).pack(fill="x", padx=16, pady=(0, 16))

        # --- alerts ---------------------------------------------------------
        alert_card = ctk.CTkFrame(scroll, fg_color=colors["card"], corner_radius=14)
        alert_card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(alert_card, text=f"\U0001F514 {t('alerts', self.language)}",
                     text_color=colors["text"],
                     font=ctk.CTkFont(size=14, weight="bold"),
                     anchor="w").pack(fill="x", padx=16, pady=(14, 10))

        add_row = ctk.CTkFrame(alert_card, fg_color="transparent")
        add_row.pack(fill="x", padx=16, pady=(0, 8))
        self.alert_from_var      = ctk.StringVar(value=self.from_code)
        self.alert_to_var        = ctk.StringVar(value=self.to_code)
        self.alert_dir_var       = ctk.StringVar(value="above")
        self.alert_threshold_var = ctk.StringVar(value="")

        ctk.CTkOptionMenu(add_row, values=list(CURRENCIES.keys()),
                          variable=self.alert_from_var, width=80, **om_kw).pack(side="left", padx=2)
        ctk.CTkLabel(add_row, text="\u2192",
                     text_color=colors["text_dim"]).pack(side="left", padx=2)
        ctk.CTkOptionMenu(add_row, values=list(CURRENCIES.keys()),
                          variable=self.alert_to_var, width=80, **om_kw).pack(side="left", padx=2)
        ctk.CTkOptionMenu(add_row, values=["above", "below"],
                          variable=self.alert_dir_var, width=80, **om_kw).pack(side="left", padx=6)
        ctk.CTkEntry(add_row, textvariable=self.alert_threshold_var,
                     placeholder_text="Threshold",
                     text_color=colors["text"], width=90, height=32).pack(side="left", padx=2)
        ctk.CTkButton(add_row, text=t("add_alert", self.language),
                      width=100, height=32, corner_radius=8,
                      fg_color=colors["accent"], hover_color=colors["accent_hover"],
                      text_color="#FFFFFF",
                      command=self._add_alert).pack(side="left", padx=6)

        self.alerts_list_frame = ctk.CTkFrame(alert_card, fg_color="transparent")
        self.alerts_list_frame.pack(fill="x", padx=16, pady=(0, 16))
        self._refresh_alerts_list()

    def _on_theme_switch(self, value: str) -> None:
        new_mode = "dark" if value == t("dark_mode", self.language) else "light"
        self._apply_theme(new_mode)

    def _apply_theme(self, mode: str) -> None:
        self.theme_mode = mode
        ctk.set_appearance_mode(mode)
        colors = palette(mode)
        self.configure(fg_color=colors["bg"])
        self.header_frame.configure(fg_color=colors["surface"])
        self.title_label.configure(text_color=colors["text"])
        self.subtitle_label.configure(text_color=colors["text_dim"])
        for btn in (self.keypad_btn, self.mini_btn):
            btn.configure(fg_color=colors["surface_alt"],
                          hover_color=colors["accent_soft"],
                          text_color=colors["text"])
        # Explicitly re-theme the persistent CTkTabview — its segmented
        # button bar is not destroyed/rebuilt with the tab contents, so
        # it must be reconfigured directly whenever the theme changes.
        self.tabview.configure(
            fg_color=colors["surface"],
            segmented_button_fg_color=colors["surface_alt"],
            segmented_button_selected_color=colors["accent"],
            segmented_button_selected_hover_color=colors["accent_hover"],
            segmented_button_unselected_color=colors["surface_alt"],
            segmented_button_unselected_hover_color=colors["accent_soft"],
            text_color=colors["text"])
        self._wire_ttk_style()
        self._rebuild_tabs()

    def _rebuild_tabs(self) -> None:
        """
        Tear down and rebuild all tab contents in the new theme.
        This is simpler and safer than patching every nested widget.
        """
        preserved_amount = self.amount_var.get() if hasattr(self, "amount_var") else "100"
        preserved_search = self.history_search_var.get() if hasattr(self, "history_search_var") else ""

        # CTkScrollableFrame registers a <MouseWheel> handler via bind_all
        # but never removes it on destroy(). Without this cleanup, every
        # theme toggle stacks another dead global binding — which breaks
        # trackpad / scroll-wheel scrolling after the first switch.
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<KeyPress-Shift_L>")
        self.unbind_all("<KeyPress-Shift_R>")
        self.unbind_all("<KeyRelease-Shift_L>")
        self.unbind_all("<KeyRelease-Shift_R>")

        if hasattr(self, "graph_manager"):
            import matplotlib.pyplot as plt
            plt.close(self.graph_manager.figure)

        for tab in (self.tab_converter, self.tab_history, self.tab_graph, self.tab_settings):
            for child in tab.winfo_children():
                child.destroy()

        self._build_converter_tab(self.tab_converter)
        self._build_history_tab(self.tab_history)
        self._build_graph_tab(self.tab_graph)
        self._build_settings_tab(self.tab_settings)

        self.amount_var.set(preserved_amount)
        self.history_search_var.set(preserved_search)
        self._refresh_history_table()

    def _save_settings(self) -> None:
        try:
            refresh_secs = int(self.refresh_var.get())
        except ValueError:
            messagebox.showerror("Invalid value",
                                 "Auto-refresh interval must be a whole number.")
            return
        self.settings.update(
            theme=self.theme_mode,
            default_from=self.settings_from_var.get(),
            default_to=self.settings_to_var.get(),
            decimal_precision=int(self.precision_var.get()),
            auto_refresh_seconds=max(0, refresh_secs),
            language=self.language_var.get())
        self.language = self.language_var.get()
        self._schedule_auto_refresh()
        messagebox.showinfo("Settings saved", "Your preferences have been saved.")

    # ----------------------------------------------------------- alerts UI
    def _add_alert(self) -> None:
        try:
            threshold = float(self.alert_threshold_var.get())
        except ValueError:
            messagebox.showerror("Invalid threshold", "Enter a numeric threshold.")
            return
        self.alerts.add(self.alert_from_var.get(), self.alert_to_var.get(),
                        self.alert_dir_var.get(), threshold)
        self.alert_threshold_var.set("")
        self._refresh_alerts_list()

    def _refresh_alerts_list(self) -> None:
        for child in self.alerts_list_frame.winfo_children():
            child.destroy()
        colors = palette(self.theme_mode)
        if not self.alerts.alerts:
            ctk.CTkLabel(self.alerts_list_frame,
                         text=t("no_alerts", self.language),
                         text_color=colors["text_faint"],
                         font=ctk.CTkFont(size=11)).pack(anchor="w")
            return
        for idx, alert in enumerate(self.alerts.alerts):
            row = ctk.CTkFrame(self.alerts_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            status = " \u2713 triggered" if alert.triggered else ""
            ctk.CTkLabel(row, text=alert.label() + status,
                         text_color=colors["text_dim"],
                         font=ctk.CTkFont(size=11), anchor="w").pack(
                side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="\u2715", width=26, height=26, corner_radius=8,
                          fg_color="transparent", hover_color=colors["danger"],
                          text_color=colors["text_dim"],
                          command=lambda i=idx: self._remove_alert(i)).pack(side="right")

    def _remove_alert(self, index: int) -> None:
        self.alerts.remove(index)
        self._refresh_alerts_list()

    # ============================================================ AUTO-REFRESH
    def _schedule_auto_refresh(self) -> None:
        if self._auto_refresh_job is not None:
            try:
                self.after_cancel(self._auto_refresh_job)
            except ValueError:
                pass
        seconds = int(self.settings.get("auto_refresh_seconds"))
        if seconds <= 0:
            return
        self._auto_refresh_job = self.after(seconds * 1000, self._auto_refresh_tick)

    def _auto_refresh_tick(self) -> None:
        threading.Thread(target=self._auto_refresh_worker, daemon=True).start()
        self._schedule_auto_refresh()

    def _auto_refresh_worker(self) -> None:
        rate, status, ts = self.engine.get_rate_only(self.from_code, self.to_code)
        if rate is None:
            return
        fired = self.alerts.check(self.from_code, self.to_code, rate)
        def apply():
            self.status_badge.set_status(status)
            self.updated_label.configure(
                text=f"{t('last_updated', self.language)}: {ts.strftime('%Y-%m-%d %H:%M:%S')}")
            for alert in fired:
                messagebox.showinfo("Exchange Rate Alert", f"Alert triggered: {alert.label()}")
            if fired:
                self._refresh_alerts_list()
        self.after(0, apply)

    def _wire_ttk_style(self) -> None:
        colors = palette(self.theme_mode)
        style  = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview",
                        background=colors["surface"],
                        fieldbackground=colors["surface"],
                        foreground=colors["text"], rowheight=26, borderwidth=0)
        style.configure("Treeview.Heading",
                        background=colors["surface_alt"],
                        foreground=colors["text"],
                        relief="flat", font=("Segoe UI", 10, "bold"))
        style.map("Treeview",
                  background=[("selected", colors["accent"])],
                  foreground=[("selected", "#FFFFFF")])

    def _on_close(self) -> None:
        self.settings.update(theme=self.theme_mode)
        self.destroy()
