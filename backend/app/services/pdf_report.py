"""
Geração de PDF de um teste (tentativa) — relatório para o admin.

Usa fpdf2 (puro Python, sem dependências de sistema). Fontes core usam latin-1;
o texto é sanitizado para evitar erros com caracteres fora do conjunto.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from fpdf import FPDF

ORANGE = (255, 105, 0)
GREEN = (46, 125, 50)
RED = (198, 40, 40)
GREY = (110, 110, 110)
DARK = (26, 26, 26)


def _s(text: str) -> str:
    """Sanitiza para latin-1 (fonte core do fpdf), substituindo o que não couber."""
    if text is None:
        return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def _fmt_date(iso: str | None) -> str:
    if not iso:
        return "-"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso


class _PDF(FPDF):
    title_text = "Databricks Certifica"

    def header(self):
        self.set_fill_color(*ORANGE)
        self.rect(0, 0, 210, 18, "F")
        self.set_y(5)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, _s("Databricks Certifica  -  Relatorio de Simulado"), align="L")
        self.ln(16)
        self.set_text_color(*DARK)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 8, _s(f"Pagina {self.page_no()}  -  As questoes deste simulador sao de pratica "
                           "e nao refletem o exame oficial."), align="C")


def build_attempt_pdf(meta: dict, answers: List[dict], pass_mark: int = 70) -> bytes:
    pdf = _PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Cabeçalho do aluno/tentativa ──────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _s(meta.get("certification_name", "")), ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 6, _s(f"Aluno: {meta.get('user_name')} <{meta.get('user_email')}>"), ln=1)
    pdf.cell(0, 6, _s(f"Data: {_fmt_date(meta.get('created_at'))}"), ln=1)
    pdf.set_text_color(*DARK)

    passed = bool(meta.get("passed"))
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*(GREEN if passed else RED))
    verdict = "APROVADO" if passed else "REPROVADO"
    pdf.cell(0, 7, _s(f"{meta.get('score_pct')}%  -  {verdict}  (corte {pass_mark}%)"), ln=1)
    pdf.set_text_color(*GREY)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, _s(f"Acertos: {meta.get('correct')}/{meta.get('total')}   "
                      f"Questoes repetidas de tentativas anteriores: {meta.get('repeated_questions', 0)}"), ln=1)
    pdf.set_text_color(*DARK)
    pdf.ln(3)
    pdf.set_draw_color(*ORANGE)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # ── Questões ──────────────────────────────────────────────────────────────
    W = pdf.epw  # largura útil da página
    letters = "ABCDEFGH"
    for i, a in enumerate(answers, 1):
        correct_set = set(a.get("correct_answers", []))
        sel_set = set(a.get("selected", []))
        ok = a.get("is_correct")
        tag = "[OK]" if ok else "[X]"

        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*(GREEN if ok else RED))
        pdf.multi_cell(W, 6, _s(f"{tag} {i}. {a.get('question_text','')}  ({a.get('topic','')})"))
        pdf.set_text_color(*DARK)
        pdf.ln(1)

        pdf.set_font("Helvetica", "", 9)
        for oi, opt in enumerate(a.get("options", [])):
            if oi in correct_set:
                pdf.set_text_color(*GREEN); prefix = "[correta] "
            elif oi in sel_set:
                pdf.set_text_color(*RED); prefix = "[resposta do aluno] "
            else:
                pdf.set_text_color(*DARK); prefix = ""
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(W, 5, _s(f"   {letters[oi] if oi < len(letters) else oi}) {prefix}{opt}"))
        if a.get("explanation"):
            pdf.set_text_color(*GREY)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(W, 4.5, _s(f"Explicacao: {a['explanation']}"))
        pdf.set_text_color(*DARK)
        pdf.ln(3)

    out = pdf.output()
    return bytes(out)
