"""Rapports : Excel, CSV et PDF chronologique. Aucune information n'est inventée."""
import io
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import analysis
from .constants import OPEN_STATUTS, REPORT_ANOMALIES

NAVY = colors.HexColor("#0B1F3A")
EXPORT_COLS = {
    "date": "Date", "heure": "Heure événement", "saisi_le": "Saisi le", "agent": "Agent",
    "activite": "Activité", "categorie": "Catégorie", "nature": "Nature",
    "description": "Description", "action_vigie": "Action de la vigie", "informe": "Informé",
    "statut": "Statut", "priorite": "Priorité", "observations": "Observations", "id": "Identifiant",
}


def _export_df(df):
    out = df.reindex(columns=list(EXPORT_COLS)).rename(columns=EXPORT_COLS)
    return out.fillna("")


def csv_bytes(df):
    return _export_df(df).to_csv(index=False, sep=";").encode("utf-8-sig")


def excel_bytes(df):
    from openpyxl.utils import get_column_letter
    out = _export_df(df)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        out.to_excel(w, index=False, sheet_name="Événements")
        ws = w.sheets["Événements"]
        ws.freeze_panes = "A2"
        for i, col in enumerate(out.columns, 1):
            longest = max([len(str(col))] + [len(str(v)) for v in out[col].head(300)])
            ws.column_dimensions[get_column_letter(i)].width = min(60, longest + 2)
    return buf.getvalue()


# --------------------------------------------------------------------------- PDF
def _esc(t):
    return escape(str(t or "")).replace("\n", "<br/>")


def _table(sub, cell, head):
    w = [17, 38, 31, 70, 24]
    rows = [[Paragraph(h, head) for h in ("Heure", "Catégorie / nature", "Agent / activité",
                                          "Description, action, information", "Statut")]]
    for r in sub.to_dict("records"):
        desc = _esc(r["description"]) or "—"
        for label, key in (("Action de la vigie", "action_vigie"), ("Informé", "informe"),
                           ("Observations", "observations")):
            if r[key]:
                desc += f"<br/><b>{label} :</b> {_esc(r[key])}"
        if r["historique"]:
            desc += f"<br/><font size=6.5 color='#64748B'>(modifié {len(r['historique'])} fois)</font>"
        rows.append([
            Paragraph(f"<b>{_esc(r['heure'])}</b><br/><font size=6.5 color='#64748B'>{_esc(analysis.saisie_label(r))}</font>", cell),
            Paragraph(f"<b>{_esc(r['categorie'])}</b><br/>{_esc(r['nature'])}", cell),
            Paragraph(f"{_esc(r['agent']) or '—'}<br/>{_esc(r['activite']) or '—'}", cell),
            Paragraph(desc, cell),
            Paragraph(f"{_esc(r['statut'])}<br/>Priorité : {_esc(r['priorite'])}", cell),
        ])
    t = Table(rows, colWidths=[x * mm for x in w], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FB")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(15 * mm, 9 * mm, "VIGIE LOGBOOK - Document établi à partir des seuls faits enregistrés ; "
                                      "aucune information n'a été ajoutée ni déduite.")
    canvas.drawRightString(195 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def pdf_bytes(day_iso, df):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm,
                            bottomMargin=18 * mm, title=f"VIGIE LOGBOOK - Compte rendu du {day_iso}",
                            author="VIGIE LOGBOOK")
    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Title"], fontName="Helvetica-Bold", fontSize=17, leading=20,
                        alignment=TA_LEFT, textColor=NAVY, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=base["Normal"], fontSize=10, textColor=colors.HexColor("#475569"), spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11.5,
                        textColor=NAVY, spaceBefore=12, spaceAfter=5)
    cell = ParagraphStyle("cell", parent=base["Normal"], fontSize=8, leading=10)
    head = ParagraphStyle("head", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
    body = ParagraphStyle("body", parent=base["Normal"], fontSize=9)

    n = len(df)
    count = lambda col, val: int((df[col] == val).sum()) if n else 0
    summary = (f"Événements enregistrés : <b>{n}</b> &nbsp;|&nbsp; Signalements : <b>{count('nature', 'Signalement')}</b>"
               f" &nbsp;|&nbsp; Faits constatés : <b>{count('nature', 'Fait constaté')}</b>"
               f" &nbsp;|&nbsp; Actions réalisées : <b>{count('nature', 'Action réalisée')}</b>"
               f" &nbsp;|&nbsp; En attente / en cours : <b>{int(df['statut'].isin(OPEN_STATUTS).sum()) if n else 0}</b>"
               f" &nbsp;|&nbsp; Résolus : <b>{count('statut', 'Résolu')}</b>")
    story = [Paragraph("VIGIE LOGBOOK - Compte rendu journalier", h1),
             Paragraph(_esc(analysis.fr_date(day_iso)), sub), Paragraph(summary, body)]

    def section(title, s):
        story.append(Paragraph(title, h2))
        story.append(_table(s, cell, head) if len(s) else Paragraph("Aucun événement enregistré.", body))

    section("1. Chronologie complète", df)
    section("2. Anomalies et incidents", df[df["categorie"].isin(REPORT_ANOMALIES)] if n else df)
    section("3. Interventions de la vigie",
            df[(df["nature"] == "Action réalisée") | (df["categorie"] == "Intervention de la vigie")] if n else df)
    section("4. Événements en attente ou en cours", df[df["statut"].isin(OPEN_STATUTS)] if n else df)
    section("5. Événements restés sans suite", df[df["statut"] == "Sans suite"] if n else df)
    story.append(Spacer(1, 6))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
