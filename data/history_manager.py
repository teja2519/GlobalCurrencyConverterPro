"""
data/history_manager.py

HistoryManager persists every conversion to a CSV file using pandas, and
provides search, sort, single-row delete and full-clear operations, plus
CSV/PDF export for reporting.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

import pandas as pd

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(DATA_DIR, "history.csv")

COLUMNS = ["Date", "Time", "From", "To", "Original Amount", "Converted Amount", "Rate"]


class HistoryManager:
    """CSV-backed conversion history."""

    def __init__(self, path: str = HISTORY_FILE):
        self.path = path
        self._ensure_file()

    # --------------------------------------------------------------- write
    def add_entry(self, from_code: str, to_code: str, original: float,
                  converted: float, rate: float, when: Optional[datetime] = None) -> None:
        when = when or datetime.now()
        row = {
            "Date": when.strftime("%Y-%m-%d"),
            "Time": when.strftime("%H:%M:%S"),
            "From": from_code,
            "To": to_code,
            "Original Amount": round(original, 6),
            "Converted Amount": round(converted, 6),
            "Rate": round(rate, 8),
        }
        df = self.load()
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        self._save(df)

    # ---------------------------------------------------------------- read
    def load(self) -> pd.DataFrame:
        self._ensure_file()
        try:
            return pd.read_csv(self.path, dtype={"From": str, "To": str})
        except pd.errors.EmptyDataError:
            return pd.DataFrame(columns=COLUMNS)

    def search(self, query: str) -> pd.DataFrame:
        df = self.load()
        if not query:
            return df
        query = query.strip().lower()
        mask = df.apply(lambda r: query in " ".join(str(v).lower() for v in r), axis=1)
        return df[mask]

    def sort(self, column: str, ascending: bool = True) -> pd.DataFrame:
        df = self.load()
        if column not in df.columns:
            return df
        return df.sort_values(by=column, ascending=ascending).reset_index(drop=True)

    def recent(self, limit: int = 5) -> pd.DataFrame:
        df = self.load()
        return df.tail(limit).iloc[::-1].reset_index(drop=True)

    # -------------------------------------------------------------- delete
    def delete_entry(self, row_index: int) -> bool:
        df = self.load()
        if row_index < 0 or row_index >= len(df):
            return False
        df = df.drop(index=row_index).reset_index(drop=True)
        self._save(df)
        return True

    def clear_history(self) -> None:
        self._save(pd.DataFrame(columns=COLUMNS))

    # -------------------------------------------------------------- export
    def export_csv(self, dest_path: str) -> str:
        df = self.load()
        df.to_csv(dest_path, index=False)
        return dest_path

    def export_pdf(self, dest_path: str) -> str:
        """Render the history as a clean, professional-looking PDF report."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm
        from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)
        from reportlab.lib.styles import getSampleStyleSheet

        df = self.load()
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(dest_path, pagesize=landscape(A4),
                                 leftMargin=18 * mm, rightMargin=18 * mm,
                                 topMargin=16 * mm, bottomMargin=16 * mm)
        elements = [
            Paragraph("Global Currency Converter Pro", styles["Title"]),
            Paragraph("Conversion History Report", styles["Heading2"]),
            Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]),
            Spacer(1, 10),
        ]

        if df.empty:
            elements.append(Paragraph("No conversion history recorded yet.", styles["Normal"]))
        else:
            table_data = [list(df.columns)] + df.astype(str).values.tolist()
            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5B8DEF")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F3FA")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD3E1")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            elements.append(table)

        doc.build(elements)
        return dest_path

    # ------------------------------------------------------------- private
    def _ensure_file(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            pd.DataFrame(columns=COLUMNS).to_csv(self.path, index=False)

    def _save(self, df: pd.DataFrame) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        df.to_csv(self.path, index=False)
