"""Analyse : DataFrame, filtres, recherche tolérante aux accents, indicateurs."""
import re
import unicodedata
from datetime import date, datetime

import pandas as pd

from .constants import ANOMALIES, OPEN_STATUTS
from .storage import EVENT_FIELDS

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
SEARCH_COLS = ["id", "date", "heure", "agent", "activite", "categorie", "nature", "description",
               "action_vigie", "informe", "statut", "priorite", "observations"]


def norm(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().casefold()


def fr_date(iso):
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year}"


def saisie_label(ev):
    """Rend visible la différence entre l'heure de l'événement et l'heure de saisie."""
    s = ev.get("saisi_le") or ""
    if len(s) < 16:
        return "heure de saisie inconnue"
    if s[:10] == ev.get("date"):
        return f"saisi à {s[11:16]}"
    return f"saisi le {s[8:10]}/{s[5:7]} à {s[11:16]}"


def to_df(events):
    df = pd.DataFrame(list(events)).reindex(columns=EVENT_FIELDS)
    for c in EVENT_FIELDS:
        if c != "historique":
            df[c] = df[c].fillna("").astype(str)
    df["ts"] = pd.to_datetime(df["date"] + " " + df["heure"], format="%Y-%m-%d %H:%M", errors="coerce")
    return df.sort_values(["ts", "saisi_le"], kind="stable").reset_index(drop=True)


def records(df):
    return df.drop(columns=["ts"]).to_dict("records")


_RE_H = re.compile(r"^(\d{1,2})h(\d{2})?$")
_RE_D = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})$")


def _tokens(text):
    out = []
    for tok in norm(text).split():
        m = _RE_H.match(tok)
        if m:
            tok = f"{int(m.group(1)):02d}:{m.group(2) or ''}"
        else:
            m = _RE_D.match(tok)
            if m:
                tok = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        out.append(tok)
    return out


def filter_df(df, date_from=None, date_to=None, t_from=None, t_to=None, agents=None,
              activites=None, categories=None, statuts=None, priorites=None, text=""):
    if df.empty:
        return df
    m = pd.Series(True, index=df.index)
    if date_from:
        m &= df["date"] >= date_from.isoformat()
    if date_to:
        m &= df["date"] <= date_to.isoformat()
    if t_from:
        m &= df["heure"] >= t_from.strftime("%H:%M")
    if t_to:
        m &= df["heure"] <= t_to.strftime("%H:%M")
    for col, vals in (("agent", agents), ("activite", activites), ("categorie", categories),
                      ("statut", statuts), ("priorite", priorites)):
        if vals:
            m &= df[col].isin(vals)
    if text and text.strip():
        blob = df[SEARCH_COLS].agg(" ".join, axis=1).map(norm)
        for tok in _tokens(text):
            m &= blob.str.contains(tok, regex=False)
    return df[m]


def agent_mask(df, query, include_description=True):
    q = norm(query).strip()
    if df.empty or not q:
        return pd.Series(False, index=df.index)
    m = df["agent"].map(norm).str.contains(q, regex=False)
    if include_description:
        m |= df["description"].map(norm).str.contains(q, regex=False)
    return m


def kpis(df):
    if df.empty:
        return dict(total=0, informatique=0, retards=0, ostie=0, anomalies=0, attente=0, resolus=0)
    return dict(
        total=len(df),
        informatique=int((df["categorie"] == "Problème informatique").sum()),
        retards=int((df["categorie"] == "Retard de connexion").sum()),
        ostie=int((df["categorie"] == "Départ OSTIE").sum()),
        anomalies=int(df["categorie"].isin(ANOMALIES).sum()),
        attente=int(df["statut"].isin(OPEN_STATUTS).sum()),
        resolus=int((df["statut"] == "Résolu").sum()),
    )
