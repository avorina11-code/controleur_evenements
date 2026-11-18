"""Interface : style (CSS), horloge/raccourcis (JavaScript), cartes de chronologie, formulaires, dialogues."""
import html
from datetime import date, time

import streamlit as st

from . import analysis, storage
from .constants import (CATEGORIES, DEFAULT_ACTIVITY, NATURES, NATURES_HELP, OPEN_STATUTS,
                        PRIORITE_COLORS, PRIORITES, STATUT_COLORS, STATUTS)

CSS = """
<style>
:root{--navy:#0B1F3A;--navy2:#16315C;--blue:#1D4ED8;--bg:#F3F5F9;--line:#D9E0EC;--mute:#64748B}
.stApp{background:var(--bg)}
.block-container{padding-top:4rem;max-width:1450px}
[data-testid="stHeader"]{background:rgba(243,245,249,.92)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0B1F3A 0%,#102A50 100%)}
[data-testid="stSidebar"] *{color:#E6ECF7}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:7px 10px;border-radius:8px;margin-bottom:2px}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:rgba(255,255,255,.09)}
.brand{font-size:1.25rem;letter-spacing:.02em;line-height:1.2;margin-bottom:6px}
.brand span{display:block;font-size:.72rem;opacity:.7}
.side-stat{display:flex;gap:8px;margin:10px 0}
.side-stat div{flex:1;background:rgba(255,255,255,.08);border-radius:8px;padding:6px 8px;text-align:center}
.side-stat b{display:block;font-size:1.25rem}
.side-stat small{opacity:.7;font-size:.68rem}
.hero{background:linear-gradient(120deg,#0B1F3A,#1B3C73);border-radius:12px;padding:14px 20px;margin-bottom:12px;
 display:flex;justify-content:space-between;align-items:center;gap:12px}
.hero h1{color:#fff;font-size:1.35rem;margin:0;padding:0;line-height:1.25}
.hero p{color:#B9C7E0;margin:2px 0 0;font-size:.85rem}
.hero-tag{color:#9FB4D8;font-size:.75rem;white-space:nowrap}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));gap:10px;margin:4px 0 12px}
.kpi{background:#fff;border:1px solid var(--line);border-top:3px solid var(--accent);border-radius:10px;padding:9px 12px}
.kpi .v{font-size:1.65rem;font-weight:700;color:var(--navy);line-height:1.1}
.kpi .l{font-size:.74rem;color:var(--mute)}
.ev{background:#fff;border:1px solid var(--line);border-left:6px solid #888;border-radius:10px;padding:9px 14px;margin:6px 0 2px}
.ev.crit{animation:pulse 2.4s ease-in-out infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(220,38,38,0)}50%{box-shadow:0 0 0 4px rgba(220,38,38,.16)}}
@media (prefers-reduced-motion:reduce){.ev.crit{animation:none}}
.ev-top{display:flex;flex-wrap:wrap;align-items:center;gap:7px}
.ev-time{font-family:ui-monospace,Menlo,Consolas,monospace;font-weight:700;color:var(--navy);font-size:1.05rem}
.chip{color:#fff;border-radius:999px;padding:1px 10px;font-size:.72rem;font-weight:600}
.badge{border:1px solid;border-radius:6px;padding:0 7px;font-size:.7rem;font-weight:600}
.nat{font-size:.72rem;color:var(--mute);font-style:italic}
.ev-desc{margin:5px 0 3px;color:#1E293B;line-height:1.4}
.ev-det{font-size:.8rem;color:#334155;margin:1px 0}
.ev-meta{font-size:.74rem;color:var(--mute);margin-top:3px}
.day-sep{margin:14px 0 4px;font-weight:700;color:var(--navy);border-bottom:2px solid var(--navy);padding-bottom:2px}
.li{padding:3px 0;border-bottom:1px dashed var(--line);font-size:.9rem}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{width:100%;border-radius:8px;font-weight:600}
@media (max-width:640px){.hero{flex-direction:column;align-items:flex-start}.kpi .v{font-size:1.3rem}}
</style>
"""

CLOCK = """
<div style="font-family:ui-monospace,Menlo,Consolas,monospace;color:#fff;text-align:center">
<div id="t" style="font-size:28px;font-weight:700;letter-spacing:2px">--:--:--</div>
<div id="d" style="font-size:12px;opacity:.75;text-transform:capitalize"></div></div>
<script>
const T=document.getElementById('t'),D=document.getElementById('d');
function tick(){const n=new Date();T.textContent=n.toLocaleTimeString('fr-FR');
D.textContent=n.toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long'});}
tick();setInterval(tick,1000);
try{const P=window.parent;if(!P.__vigieKeys){P.__vigieKeys=true;
P.document.addEventListener('keydown',function(e){
 if(e.altKey&&e.code==='KeyN'){const t=P.document.querySelector('textarea[aria-label="Description"]');
 if(t){t.focus();e.preventDefault();}}});}}catch(e){}
</script>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def clock():
    """Horloge en direct + raccourci Alt+N (JavaScript). Sans effet si l'iframe est indisponible."""
    try:
        if hasattr(st, "iframe"):
            st.iframe(CLOCK, height=62)
        else:
            import streamlit.components.v1 as components
            components.html(CLOCK, height=62)
    except Exception:
        pass


def esc(s):
    return html.escape(str(s or "")).replace("$", "&#36;").replace("\n", "<br>")


def hero(title, subtitle=""):
    st.markdown(f'<div class="hero"><div><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>'
                f'<div class="hero-tag">VIGIE LOGBOOK</div></div>', unsafe_allow_html=True)


def kpis(items):
    cells = "".join(f'<div class="kpi" style="--accent:{c}"><div class="v">{v}</div><div class="l">{esc(l)}</div></div>'
                    for l, v, c in items)
    st.markdown(f'<div class="kpis">{cells}</div>', unsafe_allow_html=True)


def line_item(r):
    who = f" · {esc(r['agent'])}" if r.get("agent") else ""
    return (f'<div class="li"><b>{esc(r["heure"])}</b>{who} — {esc(r["description"]) or "—"} '
            f'<span style="color:#64748B">[{esc(r["statut"])}]</span></div>')


def show_plot(fig):
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


def show_df(df, **kw):
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kw)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True, **kw)


# --------------------------------------------------------------------------- chronologie
def card_html(ev):
    col = CATEGORIES.get(ev["categorie"], "#6B7280")
    pc = PRIORITE_COLORS.get(ev["priorite"], "#64748B")
    sc = STATUT_COLORS.get(ev["statut"], "#64748B")
    crit = " crit" if ev["priorite"] == "Critique" and ev["statut"] in OPEN_STATUTS else ""
    p = [f'<div class="ev{crit}" style="border-left-color:{col}"><div class="ev-top">'
         f'<span class="ev-time">{esc(ev["heure"])}</span>'
         f'<span class="chip" style="background:{col}">{esc(ev["categorie"])}</span>'
         f'<span class="badge" style="color:{pc};border-color:{pc}">{esc(ev["priorite"])}</span>'
         f'<span class="badge" style="color:{sc};border-color:{sc}">{esc(ev["statut"])}</span>'
         f'<span class="nat">{esc(ev["nature"])}</span></div>',
         f'<div class="ev-desc">{esc(ev["description"]) or "—"}</div>']
    for label, key in (("Action de la vigie", "action_vigie"), ("Informé", "informe"), ("Observations", "observations")):
        if ev.get(key):
            p.append(f'<div class="ev-det"><b>{label} :</b> {esc(ev[key])}</div>')
    meta = []
    if ev.get("agent"):
        meta.append(f'Agent : {esc(ev["agent"])}')
    if ev.get("activite"):
        meta.append(esc(ev["activite"]))
    meta.append(esc(analysis.saisie_label(ev)))
    if ev.get("historique"):
        meta.append(f'modifié {len(ev["historique"])} fois')
    p.append(f'<div class="ev-meta">{" · ".join(meta)}</div></div>')
    return "".join(p)


def render_timeline(events, ctx, editable=True, limit=150, empty="Aucun événement pour cette sélection."):
    if not events:
        st.info(empty)
        return
    if len(events) > limit:
        st.caption(f"Affichage de {limit} événements sur {len(events)} : affinez les filtres pour voir le reste.")
        events = events[:limit]
    multi = len({e["date"] for e in events}) > 1
    last = None
    for ev in events:
        if multi and ev["date"] != last:
            st.markdown(f'<div class="day-sep">{esc(analysis.fr_date(ev["date"]))}</div>', unsafe_allow_html=True)
            last = ev["date"]
        st.markdown(card_html(ev), unsafe_allow_html=True)
        if editable:
            b1, b2, _ = st.columns([1, 1, 4])
            if b1.button("✏️ Modifier", key=f"{ctx}_ed_{ev['id']}"):
                edit_dialog(ev["id"])
            if ev["statut"] != "Résolu" and b2.button("✅ Résolu", key=f"{ctx}_ok_{ev['id']}"):
                db, _n = storage.load()
                storage.update_event(db, ev["id"], {"statut": "Résolu"})
                storage.save(db)
                st.rerun()


# --------------------------------------------------------------------------- formulaires
def activity_options(db, current=None):
    opts = [DEFAULT_ACTIVITY]
    for e in db["events"]:
        a = e.get("activite", "")
        if a and a not in opts:
            opts.append(a)
    if current and current not in opts:
        opts.append(current)
    return opts + [""]


def common_fields(p, db, ev=None):
    """Champs communs à la saisie et à la modification. Retourne un dict de valeurs."""
    e = ev or {}
    cats = list(CATEGORIES)
    k = lambda n: f"{p}_{n}"
    idx = lambda opts, v, d=0: opts.index(v) if v in opts else d

    a, b = st.columns(2)
    if ev is None:
        categorie = a.selectbox("Catégorie", cats, key=k("cat"))
    else:
        categorie = a.selectbox("Catégorie", cats, index=idx(cats, e.get("categorie"), len(cats) - 1), key=k("cat"))
    agent = b.text_input("Agent concerné (facultatif)", value=e.get("agent", ""), key=k("agent"))

    acts = activity_options(db, e.get("activite"))
    a, b = st.columns(2)
    act_sel = a.selectbox("Activité", acts, index=idx(acts, e.get("activite", DEFAULT_ACTIVITY)),
                          format_func=lambda x: x or "— non précisée —", key=k("act"))
    act_new = b.text_input("Autre activité (si non listée)", key=k("act_new"))
    description = st.text_area("Description", value=e.get("description", ""), height=100, key=k("desc"),
                               placeholder="Les faits, tels que vous les avez constatés ou reçus.")
    a, b, c = st.columns(3)
    nature = a.selectbox("Nature", NATURES, index=idx(NATURES, e.get("nature")), key=k("nat"), help=NATURES_HELP)
    statut = b.selectbox("Statut", STATUTS, index=idx(STATUTS, e.get("statut")), key=k("stat"))
    prio = c.selectbox("Priorité", PRIORITES, index=idx(PRIORITES, e.get("priorite"), 1), key=k("prio"))
    with st.expander("Détails : action de la vigie, personne informée, observations", expanded=bool(ev)):
        action = st.text_area("Action réalisée par la vigie", value=e.get("action_vigie", ""), height=70, key=k("action"))
        informe = st.text_input("Personne ou service informé", value=e.get("informe", ""), key=k("inf"))
        obs = st.text_area("Observations complémentaires", value=e.get("observations", ""), height=70, key=k("obs"))
    return {"categorie": categorie, "agent": agent, "activite": act_new.strip() or act_sel,
            "description": description, "nature": nature, "statut": statut, "priorite": prio,
            "action_vigie": action, "informe": informe, "observations": obs}


@st.dialog("Modifier / compléter l'événement", width="large")
def edit_dialog(eid):
    db, _n = storage.load()
    ev = storage.get_event(db, eid)
    if ev is None:
        st.error("Événement introuvable.")
        return
    p = f"ed{eid}"
    c1, c2 = st.columns(2)
    d = c1.date_input("Date de l'événement", value=date.fromisoformat(ev["date"]), key=f"{p}_date")
    t = c2.time_input("Heure de l'événement", value=time.fromisoformat(ev["heure"]), step=60, key=f"{p}_time")
    st.caption(f"Identifiant {ev['id']} · {analysis.saisie_label(ev)}")
    vals = common_fields(p, db, ev)
    if st.button("💾 Enregistrer les modifications", type="primary", key=f"{p}_save"):
        if not vals["description"].strip():
            st.error("La description ne peut pas être vide.")
        else:
            changes = {"date": d.isoformat(), "heure": t.strftime("%H:%M"), **vals}
            if storage.update_event(db, eid, changes):
                storage.save(db)
            st.rerun()
    if ev["historique"]:
        with st.expander(f"Historique des modifications ({len(ev['historique'])})"):
            for h in reversed(ev["historique"]):
                st.markdown(f"**{h['modifie_le']}**")
                for champ, v in h["modifications"].items():
                    st.markdown(f"- {champ} : « {v['avant']} » → « {v['apres']} »".replace("$", "\\$"))
    with st.expander("Supprimer cet événement"):
        st.caption("L'événement est déplacé dans la corbeille (Données → Corbeille) et reste récupérable.")
        ok = st.checkbox("Je confirme la suppression", key=f"{p}_delok")
        if st.button("🗑 Supprimer", disabled=not ok, key=f"{p}_del"):
            storage.delete_event(db, eid)
            storage.save(db)
            st.rerun()
