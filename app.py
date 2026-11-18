"""VIGIE LOGBOOK — journal de bord opérationnel de la vigie.  Lancer :  streamlit run app.py"""
import json
import sys
from pathlib import Path

# Garantit que le dossier « vigie/ » situé à côté de app.py est trouvé, quel que soit le répertoire de lancement.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from datetime import date, datetime, time, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from vigie import analysis, demo, reports, storage, ui
from vigie.constants import (CATEGORIES, OPEN_STATUTS, PRIORITES, QUICK_BUTTONS, STATUT_COLORS, STATUTS)

st.set_page_config(page_title="VIGIE LOGBOOK", page_icon="🧭", layout="wide")
ui.inject_css()


# =========================================================================== SAISIE & CHRONOLOGIE
def page_saisie(db):
    ui.hero("Saisie rapide & chronologie", "Un événement en quelques secondes : choisissez une catégorie, décrivez, enregistrez.")
    if msg := st.session_state.pop("_flash", None):
        st.toast(msg, icon="✅")
    if st.session_state.pop("_reset_form", False):
        for k in [k for k in st.session_state if k.startswith("f_")]:
            del st.session_state[k]
    st.session_state.setdefault("f_cat", "Autre événement")

    def set_cat(cat):
        st.session_state["f_cat"] = cat

    for col, (label, cat) in zip(st.columns(len(QUICK_BUTTONS)), QUICK_BUTTONS):
        col.button(label, key=f"q_{cat}", on_click=set_cat, args=(cat,), help=f"Catégorie : {cat}")

    left, right = st.columns([1, 1.25], gap="large")
    with left:
        st.markdown("#### Nouvel événement")
        with st.form("form_saisie", border=True):
            vals = ui.common_fields("f", db)
            with st.expander("🕒 Événement antérieur (date et heure réelles différentes de maintenant)"):
                st.caption("Par défaut, l'heure de l'événement est l'heure exacte de l'enregistrement. "
                           "Cochez pour saisir l'heure réelle d'un fait passé.")
                use_dt = st.checkbox("Saisir une date et une heure précises", key="f_use_dt")
                c1, c2 = st.columns(2)
                d = c1.date_input("Date", value=storage.today(), key="f_date")
                t = c2.time_input("Heure", value=storage.now().time().replace(second=0, microsecond=0),
                                  step=60, key="f_time")
            submitted = st.form_submit_button("➕ Enregistrer l'événement", type="primary")
        st.caption("Raccourcis : Alt+N place le curseur dans « Description » · Ctrl+Entrée valide le formulaire.")
        if submitted:
            ev_dt = datetime.combine(d, t) if use_dt else storage.now()
            if not vals["description"].strip():
                st.error("Ajoutez une courte description du fait.")
            elif ev_dt > storage.now() + timedelta(minutes=1):
                st.error("L'heure de l'événement est dans le futur : corrigez la date ou l'heure.")
            else:
                ev = storage.add_event(db, date=ev_dt.date().isoformat(), heure=ev_dt.strftime("%H:%M"), **vals)
                storage.save(db)
                st.session_state["_reset_form"] = True
                st.session_state["_flash"] = f"Événement de {ev['heure']} enregistré ({analysis.saisie_label(ev)})."
                st.rerun()

    with right:
        h1, h2 = st.columns([1, 1])
        day = h1.date_input("Journée affichée", value=storage.today(), key="home_day")
        rev = h2.toggle("Plus récent en haut", key="home_rev")
        df = analysis.to_df(db["events"])
        dday = df[df["date"] == day.isoformat()]
        k = analysis.kpis(dday)
        ui.kpis([("Événements", k["total"], "#1D4ED8"), ("En attente / en cours", k["attente"], "#EA580C"),
                 ("Résolus", k["resolus"], "#16A34A"), ("Incidents informatiques", k["informatique"], "#7C3AED")])
        recs = analysis.records(dday)
        with st.container(height=640, border=False):
            ui.render_timeline(recs[::-1] if rev else recs, "home",
                               empty="Aucun événement enregistré ce jour-là. Utilisez le formulaire ou un bouton rapide.")


# =========================================================================== JOURNÉE
def _bullets(sub, empty="Aucun événement enregistré."):
    if sub.empty:
        st.caption(empty)
    for r in sub.to_dict("records"):
        st.markdown(ui.line_item(r), unsafe_allow_html=True)


def page_journee(db):
    ui.hero("Reconstitution de la journée", "Toute la journée reconstruite à partir des seuls faits enregistrés.")
    df = analysis.to_df(db["events"])
    c1, c2, c3 = st.columns(3)
    day = c1.date_input("Date", value=storage.today(), key="j_date")
    t_from = c2.time_input("De", value=time(0, 0), step=60, key="j_from")
    t_to = c3.time_input("À", value=time(23, 59), step=60, key="j_to")
    if t_to < t_from:
        st.warning("L'heure de fin est antérieure à l'heure de début.")
    dday = df[df["date"] == day.isoformat()]
    with st.expander("Filtres : agent, activité, catégorie, statut"):
        f1, f2 = st.columns(2)
        agents = f1.multiselect("Agent", sorted({a for a in dday["agent"] if a}), key="j_ag")
        acts = f2.multiselect("Activité", sorted({a for a in dday["activite"] if a}), key="j_ac")
        cats = f1.multiselect("Catégorie", list(CATEGORIES), key="j_ca")
        stats = f2.multiselect("Statut", STATUTS, key="j_st")
    fdf = analysis.filter_df(dday, t_from=t_from, t_to=t_to, agents=agents, activites=acts,
                             categories=cats, statuts=stats)
    n = len(fdf)
    cnt = lambda col, val: int((fdf[col] == val).sum()) if n else 0
    ui.kpis([("Événements (sélection)", n, "#1D4ED8"), ("Signalements reçus", cnt("nature", "Signalement"), "#0891B2"),
             ("Faits constatés", cnt("nature", "Fait constaté"), "#475569"),
             ("Actions réalisées", cnt("nature", "Action réalisée"), "#16A34A"),
             ("En attente / en cours", int(fdf["statut"].isin(OPEN_STATUTS).sum()) if n else 0, "#EA580C"),
             ("Sans suite", cnt("statut", "Sans suite"), "#B91C1C")])

    tab1, tab2, tab3 = st.tabs(["Chronologie", "Synthèse", "Rapports"])
    with tab1:
        ui.render_timeline(analysis.records(fdf), "jour", empty="Aucun événement pour cette sélection.")
    with tab2:
        if n == 0:
            st.info("Aucun événement pour cette sélection.")
        else:
            cat = fdf["categorie"]
            sections = [
                ("Problèmes informatiques (agents concernés)", fdf[cat == "Problème informatique"]),
                ("Départs OSTIE (heures constatées ou signalées)", fdf[cat == "Départ OSTIE"]),
                ("Consignes managériales reçues", fdf[cat == "Consigne managériale"]),
                ("Interventions de la vigie", fdf[(fdf["nature"] == "Action réalisée") | (cat == "Intervention de la vigie")]),
                ("Événements non résolus (en attente / en cours)", fdf[fdf["statut"].isin(OPEN_STATUTS)]),
                ("Problèmes restés sans suite", fdf[fdf["statut"] == "Sans suite"]),
            ]
            for title, sub in sections:
                with st.expander(f"{title} — {len(sub)}", expanded=len(sub) > 0):
                    _bullets(sub)
    with tab3:
        st.caption("Les rapports portent sur toute la journée sélectionnée (hors filtres).")
        stamp = day.isoformat()
        a, b, c, d = st.columns(4)
        a.download_button("📄 PDF du jour", reports.pdf_bytes(stamp, dday), f"vigie_{stamp}.pdf", "application/pdf")
        b.download_button("📊 Excel du jour", reports.excel_bytes(dday), f"vigie_{stamp}.xlsx",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        c.download_button("📑 CSV du jour", reports.csv_bytes(dday), f"vigie_{stamp}.csv", "text/csv")
        d.download_button("💾 JSON du jour", storage.export_day(db, stamp), f"vigie_{stamp}.json", "application/json")


# =========================================================================== AGENTS
def page_agents(db):
    ui.hero("Fiche individuelle des agents", "Historique factuel et chronologique : ce n'est ni une notation ni un outil de sanction.")
    df = analysis.to_df(db["events"])
    q = st.text_input("Nom de l'agent (recherche partielle)", placeholder="ex. Rakoto", key="ag_q")
    incl = st.checkbox("Inclure les événements où le nom apparaît seulement dans la description", value=True)
    if not q.strip():
        known = df[df["agent"] != ""]["agent"].value_counts().reset_index() if not df.empty else pd.DataFrame()
        if known.empty:
            st.info("Aucun agent renseigné pour l'instant.")
        else:
            known.columns = ["Agent", "Événements"]
            st.markdown("**Agents présents dans le journal**")
            ui.show_df(known)
        return
    sub = df[analysis.agent_mask(df, q, incl)]
    names = sorted({a for a in sub["agent"] if a})
    st.markdown(f"**{len(sub)}** événement(s)" + (f" — agent(s) : {', '.join(names)}" if names else ""))
    t1, t2 = st.tabs(["Historique chronologique", "Répartition"])
    with t1:
        ui.render_timeline(analysis.records(sub), "ag", empty="Aucun événement trouvé pour ce nom.")
    with t2:
        if sub.empty:
            st.info("Aucun événement.")
        else:
            c = sub["categorie"].value_counts().reset_index()
            c.columns = ["Catégorie", "Nombre"]
            ui.show_df(c)
            st.download_button("📑 Exporter cet historique (CSV)", reports.csv_bytes(sub), "historique_agent.csv", "text/csv")


# =========================================================================== TABLEAU DE BORD
def _layout(fig, h=330):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=45, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#0B1F3A"), showlegend=False, title_font_size=15)
    return fig


def page_dashboard(db):
    ui.hero("Tableau de bord opérationnel", "Indicateurs et répartitions sur la période choisie.")
    df = analysis.to_df(db["events"])
    today = storage.today()
    periode = st.selectbox("Période", ["Aujourd'hui", "7 derniers jours", "30 derniers jours",
                                       "Période personnalisée", "Toute la période"], key="db_p")
    a = b = None
    if periode == "Aujourd'hui":
        a = b = today
    elif periode == "7 derniers jours":
        a, b = today - timedelta(days=6), today
    elif periode == "30 derniers jours":
        a, b = today - timedelta(days=29), today
    elif periode == "Période personnalisée":
        rng = st.date_input("Du … au …", value=(today - timedelta(days=6), today), key="db_rng")
        if not isinstance(rng, (tuple, list)) or len(rng) < 2:
            st.info("Choisissez la date de fin.")
            return
        a, b = rng
    fdf = analysis.filter_df(df, date_from=a, date_to=b)
    k = analysis.kpis(fdf)
    ui.kpis([("Événements", k["total"], "#1D4ED8"), ("Incidents informatiques", k["informatique"], "#7C3AED"),
             ("Retards signalés", k["retards"], "#D97706"), ("Demandes OSTIE", k["ostie"], "#2563EB"),
             ("Anomalies opérationnelles", k["anomalies"], "#DC2626"),
             ("En attente / en cours", k["attente"], "#EA580C"), ("Résolus", k["resolus"], "#16A34A")])
    if fdf.empty:
        st.info("Aucun événement sur cette période.")
        return
    c1, c2 = st.columns(2)
    cat = fdf["categorie"].value_counts().reset_index()
    cat.columns = ["Catégorie", "Nombre"]
    ui.show_plot(_layout(px.bar(cat.sort_values("Nombre"), x="Nombre", y="Catégorie", orientation="h",
                                color="Catégorie", color_discrete_map=CATEGORIES, title="Répartition par catégorie")))
    hrs = fdf["ts"].dropna().dt.hour
    if not hrs.empty:
        rng_h = range(int(hrs.min()), int(hrs.max()) + 1)
        cnt = hrs.value_counts().reindex(rng_h, fill_value=0)
        hd = pd.DataFrame({"Heure": [f"{h:02d}h" for h in rng_h], "Événements": cnt.values})
        fig = px.bar(hd, x="Heure", y="Événements", title="Évolution horaire (cumul de la période)")
        fig.update_traces(marker_color="#1D4ED8")
        ui.show_plot(_layout(fig))
    c3, c4 = st.columns(2)
    act = fdf["activite"].replace("", "Non précisée").value_counts().reset_index()
    act.columns = ["Activité", "Nombre"]
    fig = px.bar(act, x="Activité", y="Nombre", title="Volume par activité")
    fig.update_traces(marker_color="#16315C")
    with c3:
        ui.show_plot(_layout(fig))
    st_df = fdf["statut"].value_counts().reset_index()
    st_df.columns = ["Statut", "Nombre"]
    with c4:
        ui.show_plot(_layout(px.pie(st_df, names="Statut", values="Nombre", hole=0.5, color="Statut",
                                    color_discrete_map=STATUT_COLORS, title="Répartition par statut")))


# =========================================================================== RECHERCHE
def page_recherche(db):
    ui.hero("Recherche globale", "Nom, mot-clé, catégorie, date (18/11/2026), heure (08h12), activité, description, statut…")
    df = analysis.to_df(db["events"])
    q = st.text_input("🔎 Rechercher", placeholder="ex. rakoto pc  ·  08h12  ·  18/11/2026  ·  OSTIE", key="s_q")
    cats = sts = acts = prios = None
    d1 = d2 = t1 = t2 = None
    with st.expander("Filtres avancés"):
        a, b = st.columns(2)
        cats = a.multiselect("Catégorie", list(CATEGORIES), key="s_ca")
        sts = b.multiselect("Statut", STATUTS, key="s_st")
        acts = a.multiselect("Activité", sorted({x for x in df["activite"] if x}) if not df.empty else [], key="s_ac")
        prios = b.multiselect("Priorité", PRIORITES, key="s_pr")
        if st.checkbox("Limiter à une période", key="s_per"):
            r = st.date_input("Du … au …", value=(storage.today() - timedelta(days=7), storage.today()), key="s_rng")
            if isinstance(r, (tuple, list)) and len(r) == 2:
                d1, d2 = r
        if st.checkbox("Limiter à une plage horaire", key="s_hr"):
            x, y = st.columns(2)
            t1 = x.time_input("De", value=time(0, 0), step=60, key="s_t1")
            t2 = y.time_input("À", value=time(23, 59), step=60, key="s_t2")
    res = analysis.filter_df(df, d1, d2, t1, t2, None, acts, cats, sts, prios, q)
    c1, c2 = st.columns([2, 1])
    c1.markdown(f"**{len(res)}** résultat(s) sur {len(df)} événement(s).")
    newest = c2.toggle("Plus récents d'abord", value=True, key="s_new")
    mode = st.radio("Affichage", ["Chronologie", "Tableau"], horizontal=True, key="s_mode")
    if res.empty:
        st.info("Aucun résultat. Essayez moins de mots ou retirez des filtres.")
        return
    res = res.iloc[::-1] if newest else res
    if mode == "Tableau":
        ui.show_df(res[["date", "heure", "agent", "activite", "categorie", "nature", "description", "statut", "priorite"]])
    else:
        ui.render_timeline(analysis.records(res), "rech")
    st.download_button("📑 Exporter ces résultats (CSV)", reports.csv_bytes(res), "recherche_vigie.csv", "text/csv")


# =========================================================================== DONNÉES
def page_donnees(db):
    ui.hero("Données & sauvegardes", "Export, import par fusion (sans écrasement), sauvegardes, corbeille, démonstration.")
    if msg := st.session_state.pop("_flash2", None):
        st.success(msg)
    df = analysis.to_df(db["events"])
    t_exp, t_imp, t_bak, t_tr, t_demo = st.tabs(["Exporter", "Importer", "Sauvegardes", "Corbeille", "Démonstration"])

    with t_exp:
        stamp = storage.now().strftime("%Y%m%d_%H%M")
        st.download_button("💾 Sauvegarde complète (JSON réimportable)", storage.export_all(db),
                           f"vigie_logbook_complet_{stamp}.json", "application/json")
        st.markdown("**Journée précise**")
        day = st.date_input("Date", value=storage.today(), key="x_day")
        dd = df[df["date"] == day.isoformat()] if not df.empty else df
        a, b, c, d = st.columns(4)
        a.download_button("JSON du jour", storage.export_day(db, day.isoformat()), f"vigie_{day}.json", "application/json")
        b.download_button("PDF du jour", reports.pdf_bytes(day.isoformat(), dd), f"vigie_{day}.pdf", "application/pdf")
        c.download_button("Excel du jour", reports.excel_bytes(dd), f"vigie_{day}.xlsx",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        d.download_button("CSV du jour", reports.csv_bytes(dd), f"vigie_{day}.csv", "text/csv")
        st.markdown("**Historique complet**")
        a, b = st.columns(2)
        a.download_button("📊 Excel — tout l'historique", reports.excel_bytes(df), f"vigie_historique_{stamp}.xlsx",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        b.download_button("📑 CSV — exploitation statistique", reports.csv_bytes(df), f"vigie_historique_{stamp}.csv", "text/csv")

    with t_imp:
        st.info("L'import **fusionne** : les événements dont l'identifiant existe déjà ne sont jamais écrasés. "
                "Une sauvegarde de votre base est créée avant toute fusion.")
        up = st.file_uploader("Fichier JSON VIGIE LOGBOOK", type=["json"], key="imp_file")
        if up is not None:
            try:
                data = json.loads(up.getvalue().decode("utf-8-sig"))
                if isinstance(data, list):
                    data = {"events": data}
            except Exception as exc:
                st.error(f"Fichier illisible ou corrompu : {exc}")
                data = None
            if data is not None:
                errs = storage.validate(data)
                if errs:
                    st.error("Structure invalide — import impossible.")
                    for e in errs[:15]:
                        st.write("• " + e)
                    if len(errs) > 15:
                        st.write(f"… et {len(errs) - 15} autre(s) erreur(s).")
                else:
                    to_add, same, conflicts = storage.analyze_import(db, data["events"])
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Nouveaux événements", len(to_add))
                    m2.metric("Doublons identiques ignorés", same)
                    m3.metric("Conflits d'identifiant", len(conflicts))
                    keep_copies = False
                    if conflicts:
                        st.warning("Les événements en conflit existent déjà avec un contenu différent : "
                                   "vos versions sont conservées telles quelles.")
                        keep_copies = st.checkbox("Importer aussi les versions en conflit comme nouveaux événements "
                                                  "(nouvel identifiant)", key="imp_copies")
                    if st.button("🔀 Fusionner avec mes données", type="primary", disabled=not (to_add or (conflicts and keep_copies))):
                        db["events"].extend(to_add)
                        if keep_copies:
                            db["events"].extend(storage.as_copy(c) for c in conflicts)
                        storage.save(db, force_backup=True)
                        added = len(to_add) + (len(conflicts) if keep_copies else 0)
                        st.session_state["_flash2"] = f"{added} événement(s) ajouté(s). Rien n'a été écrasé."
                        st.rerun()

    with t_bak:
        st.caption(f"Fichier de travail : {storage.DB_FILE} — sauvegarde automatique après chaque événement.")
        if st.button("Créer une sauvegarde maintenant"):
            storage.save(db, force_backup=True)
            st.session_state["_flash2"] = "Sauvegarde créée."
            st.rerun()
        backups = storage.list_backups()
        if not backups:
            st.info("Aucune sauvegarde pour l'instant.")
        else:
            def label(p):
                try:
                    return datetime.strptime(p.stem[8:], "%Y%m%d_%H%M%S").strftime("%d/%m/%Y %H:%M:%S")
                except ValueError:
                    return p.name
            sel = st.selectbox("Sauvegarde à restaurer", backups, format_func=label, key="bak_sel")
            try:
                n = len(storage.read_json_file(sel).get("events", []))
                st.caption(f"{n} événement(s) dans cette sauvegarde · {len(db['events'])} actuellement.")
            except Exception:
                st.error("Cette sauvegarde est illisible.")
            ok = st.checkbox("Je comprends que la base actuelle sera remplacée (elle est sauvegardée avant)", key="bak_ok")
            if st.button("♻️ Restaurer cette sauvegarde", disabled=not ok):
                try:
                    _db, errs = storage.restore_backup(sel)
                except Exception as exc:
                    errs = [str(exc)]
                if errs:
                    st.error("Restauration impossible : " + errs[0])
                else:
                    st.session_state["_flash2"] = "Sauvegarde restaurée."
                    st.rerun()

    with t_tr:
        if not db["corbeille"]:
            st.info("La corbeille est vide.")
        for it in reversed(db["corbeille"]):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{it['date']} {it['heure']}** — {it['categorie']} — {it['description'][:90]}".replace("$", "\\$")
                        + f"  \n<small>supprimé le {it.get('supprime_le', '?')}</small>", unsafe_allow_html=True)
            if c2.button("Restaurer", key=f"tr_{it['id']}"):
                storage.restore_from_trash(db, it["id"])
                storage.save(db)
                st.rerun()

    with t_demo:
        st.caption("Ajoute les exemples du cahier des charges à la date du jour (identifiants « demo… »).")
        a, b = st.columns(2)
        if a.button("Charger les données de démonstration"):
            to_add, _same, _c = storage.analyze_import(db, demo.demo_events())
            db["events"].extend(to_add)
            storage.save(db, force_backup=True)
            st.session_state["_flash2"] = f"{len(to_add)} événement(s) de démonstration ajouté(s)."
            st.rerun()
        if b.button("Supprimer les données de démonstration"):
            ids = [e["id"] for e in db["events"] if e["id"].startswith("demo")]
            for i in ids:
                storage.delete_event(db, i)
            storage.save(db, force_backup=True)
            st.session_state["_flash2"] = f"{len(ids)} événement(s) de démonstration déplacé(s) dans la corbeille."
            st.rerun()


# =========================================================================== NAVIGATION
PAGES = {
    "⚡ Saisie & chronologie": page_saisie,
    "🗓 Journée": page_journee,
    "👤 Agents": page_agents,
    "📊 Tableau de bord": page_dashboard,
    "🔎 Recherche": page_recherche,
    "💾 Données & sauvegardes": page_donnees,
}

db, notice = storage.load()
if notice:
    st.session_state["_notice"] = notice
if st.session_state.get("_notice"):
    st.warning(st.session_state["_notice"])
    if st.button("J'ai compris", key="notice_ok"):
        del st.session_state["_notice"]
        st.rerun()

with st.sidebar:
    st.markdown('<div class="brand">🧭 <b>VIGIE LOGBOOK</b><span>Mémoire opérationnelle de la vigie</span></div>',
                unsafe_allow_html=True)
    ui.clock()
    page = st.radio("Navigation", list(PAGES), label_visibility="collapsed")
    today_iso = storage.today().isoformat()
    today_ev = [e for e in db["events"] if e["date"] == today_iso]
    pending = sum(1 for e in today_ev if e["statut"] in OPEN_STATUTS)
    st.markdown(f'<div class="side-stat"><div><b>{len(today_ev)}</b><small>événements du jour</small></div>'
                f'<div><b>{pending}</b><small>à suivre</small></div></div>', unsafe_allow_html=True)
    st.caption("💾 Sauvegarde automatique après chaque événement.")

PAGES[page](db)
