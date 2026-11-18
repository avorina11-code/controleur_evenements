"""Stockage JSON fiable : écriture atomique, sauvegardes, validation, fusion sans écrasement."""
import json
import os
import shutil
import time as _time
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_FILE = DATA_DIR / "logbook.json"
BACKUP_DIR = DATA_DIR / "backups"
MAX_BACKUPS = 200
BACKUP_EVERY_SEC = 120
SCHEMA_VERSION = 1
APP_NAME = "VIGIE LOGBOOK"

EDITABLE = ["date", "heure", "agent", "activite", "categorie", "nature", "description",
            "action_vigie", "informe", "statut", "priorite", "observations"]
EVENT_FIELDS = ["id", "date", "heure", "saisi_le", "agent", "activite", "categorie", "nature",
                "description", "action_vigie", "informe", "statut", "priorite", "observations",
                "historique"]


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_id():
    return uuid.uuid4().hex[:12]


# --------------------------------------------------------------------------- structure
def empty_db():
    n = _now()
    return {"application": APP_NAME, "version": SCHEMA_VERSION, "cree_le": n, "modifie_le": n,
            "events": [], "corbeille": []}


def blank_event():
    return {"id": "", "date": "", "heure": "", "saisi_le": "", "agent": "", "activite": "",
            "categorie": "Autre événement", "nature": "Signalement", "description": "",
            "action_vigie": "", "informe": "", "statut": "En attente", "priorite": "Normale",
            "observations": "", "historique": []}


def normalize_event(e):
    out = blank_event()
    for k in out:
        v = e.get(k)
        if v is None:
            continue
        if k == "historique":
            out[k] = v if isinstance(v, list) else []
        else:
            out[k] = str(v).strip() if k != "description" else str(v)
    return out


def normalize_db(data):
    db = empty_db()
    db["cree_le"] = str(data.get("cree_le") or db["cree_le"])
    seen = set()
    for e in data.get("events", []):
        ev = normalize_event(e)
        if ev["id"] and ev["id"] not in seen:
            seen.add(ev["id"])
            db["events"].append(ev)
    for e in data.get("corbeille", []) or []:
        if isinstance(e, dict) and e.get("id"):
            ev = normalize_event(e)
            ev["supprime_le"] = str(e.get("supprime_le", ""))
            db["corbeille"].append(ev)
    return db


def validate(data):
    """Retourne la liste des erreurs de structure (vide = fichier valide)."""
    if not isinstance(data, dict):
        return ["La racine du fichier doit être un objet JSON."]
    events = data.get("events")
    if not isinstance(events, list):
        return ["La clé « events » est absente ou invalide (une liste est attendue)."]
    errs = []
    for i, e in enumerate(events, 1):
        if not isinstance(e, dict):
            errs.append(f"Événement n°{i} : objet attendu.")
            continue
        for k in ("id", "date", "heure", "categorie"):
            v = e.get(k)
            if not isinstance(v, str) or not v.strip():
                errs.append(f"Événement n°{i} : champ « {k} » manquant ou vide.")
        if not isinstance(e.get("description", ""), str):
            errs.append(f"Événement n°{i} : « description » doit être du texte.")
        for k, fmt in (("date", "%Y-%m-%d"), ("heure", "%H:%M")):
            if isinstance(e.get(k), str) and e[k].strip():
                try:
                    datetime.strptime(e[k], fmt)
                except ValueError:
                    errs.append(f"Événement n°{i} : « {k} » invalide ({e[k]!r}).")
    return errs


def read_json_file(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- fichiers
def _atomic_write(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def list_backups():
    if not BACKUP_DIR.exists():
        return []
    return sorted(BACKUP_DIR.glob("logbook_*.json"), reverse=True)


def _backup(force=False):
    if not DB_FILE.exists() or DB_FILE.stat().st_size == 0:
        return
    existing = list_backups()
    if not force and existing and _time.time() - existing[0].stat().st_mtime < BACKUP_EVERY_SEC:
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DB_FILE, BACKUP_DIR / f"logbook_{datetime.now():%Y%m%d_%H%M%S}.json")
    for old in list_backups()[MAX_BACKUPS:]:
        old.unlink(missing_ok=True)


def save(db, force_backup=False):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db["modifie_le"] = _now()
    _backup(force_backup)
    _atomic_write(DB_FILE, db)


def load():
    """Charge la base. Retourne (db, message). Gère un fichier corrompu sans rien perdre."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_FILE.exists():
        return empty_db(), None
    try:
        data = read_json_file(DB_FILE)
        errs = validate(data)
        if errs:
            raise ValueError(errs[0])
        return normalize_db(data), None
    except Exception as exc:  # fichier illisible ou invalide
        aside = DATA_DIR / f"logbook_CORROMPU_{datetime.now():%Y%m%d_%H%M%S}.json"
        shutil.copyfile(DB_FILE, aside)
        for b in list_backups():
            try:
                data = read_json_file(b)
                if not validate(data):
                    db = normalize_db(data)
                    _atomic_write(DB_FILE, db)
                    return db, (f"Le fichier de données était corrompu ({exc}). Il a été conservé sous "
                                f"« {aside.name} » et la dernière sauvegarde valide ({b.name}) a été restaurée.")
            except Exception:
                continue
        return empty_db(), (f"Le fichier de données était corrompu ({exc}) et aucune sauvegarde valide n'existe. "
                            f"Il a été conservé sous « {aside.name} ». Une base vide est utilisée.")


def restore_backup(path):
    """Remplace la base courante par une sauvegarde (la base actuelle est d'abord sauvegardée)."""
    data = read_json_file(path)
    errs = validate(data)
    if errs:
        return None, errs
    db = normalize_db(data)
    save(db, force_backup=True)
    return db, []


# --------------------------------------------------------------------------- événements
def get_event(db, eid):
    return next((e for e in db["events"] if e["id"] == eid), None)


def add_event(db, **fields):
    ev = blank_event()
    for k, v in fields.items():
        if k in ev and k != "historique":
            ev[k] = v.strip() if isinstance(v, str) and k != "description" else v
    ev["id"] = new_id()
    ev["saisi_le"] = _now()
    db["events"].append(ev)
    return ev


def update_event(db, eid, changes):
    ev = get_event(db, eid)
    if ev is None:
        return False
    diff = {}
    for k, new in changes.items():
        if k in EDITABLE:
            new = new.strip() if isinstance(new, str) and k != "description" else new
            if ev[k] != new:
                diff[k] = {"avant": ev[k], "apres": new}
    if not diff:
        return False
    for k, d in diff.items():
        ev[k] = d["apres"]
    ev["historique"].append({"modifie_le": _now(), "modifications": diff})
    return True


def delete_event(db, eid):
    ev = get_event(db, eid)
    if ev is None:
        return False
    db["events"] = [e for e in db["events"] if e["id"] != eid]
    ev = dict(ev)
    ev["supprime_le"] = _now()
    db["corbeille"].append(ev)
    return True


def restore_from_trash(db, eid):
    item = next((e for e in db["corbeille"] if e["id"] == eid), None)
    if item is None:
        return False
    db["corbeille"] = [e for e in db["corbeille"] if e["id"] != eid]
    if get_event(db, eid) is None:
        ev = {k: v for k, v in item.items() if k != "supprime_le"}
        db["events"].append(normalize_event(ev))
    return True


# --------------------------------------------------------------------------- import / export
def analyze_import(db, events):
    """Compare les événements importés à la base. Ne modifie jamais db.
    Retourne (nouveaux, nb_identiques, conflits)."""
    existing = {e["id"]: e for e in db["events"]}
    to_add, conflicts, same, seen = [], [], 0, set()
    for raw in events:
        e = normalize_event(raw)
        if e["id"] in seen:
            same += 1
            continue
        seen.add(e["id"])
        cur = existing.get(e["id"])
        if cur is None:
            to_add.append(e)
        elif all(cur[k] == e[k] for k in EDITABLE):
            same += 1
        else:
            conflicts.append(e)
    return to_add, same, conflicts


def as_copy(ev):
    """Copie d'un événement en conflit, sous un nouvel identifiant (traçable dans l'historique)."""
    c = json.loads(json.dumps(ev))
    old = c["id"]
    c["id"] = new_id()
    c["historique"].append({"modifie_le": _now(), "modifications": {
        "import": {"avant": "", "apres": f"copie importée (conflit sur l'identifiant {old})"}}})
    return c


def export_all(db):
    out = dict(db)
    out["exporte_le"] = _now()
    return dumps(out)


def export_day(db, iso_day):
    evs = [e for e in db["events"] if e["date"] == iso_day]
    return dumps({"application": APP_NAME, "version": SCHEMA_VERSION, "exporte_le": _now(),
                  "date": iso_day, "events": evs})
