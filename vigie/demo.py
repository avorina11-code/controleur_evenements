"""Données de démonstration (identifiants préfixés « demo », supprimables en un clic)."""
from datetime import date

from . import storage

# (heure, catégorie, nature, agent, description, action vigie, informé, statut, priorité)
_ROWS = [
    ("08:00", "Autre événement", "Action réalisée", "", "Prise de poste de la vigie.", "", "", "Information", "Basse"),
    ("08:12", "Problème informatique", "Signalement", "Rakoto",
     "Rakoto signale que son PC ne démarre pas. Retard de connexion consécutif à une panne informatique.",
     "", "", "Résolu", "Haute"),
    ("08:24", "Retard de connexion", "Fait constaté", "R.", "Agent R. connecté après intervention technique.",
     "", "", "Résolu", "Normale"),
    ("09:15", "Départ OSTIE", "Signalement", "M.", "Agent M. signale une demande de départ en pause OSTIE.",
     "", "", "En cours", "Normale"),
    ("09:20", "Départ OSTIE", "Fait constaté", "M.", "Départ OSTIE constaté.", "", "", "Résolu", "Normale"),
    ("10:05", "Consigne managériale", "Signalement", "", "Le manager demande le renforcement de l'activité MVola.",
     "", "Manager", "En cours", "Haute"),
    ("10:12", "Basculement d'activité", "Action réalisée", "",
     "Basculement de deux agents depuis une autre activité.", "Basculement effectué", "", "Résolu", "Normale"),
    ("11:30", "Problème d'adhérence", "Fait constaté", "X.", "Agent X. présente une anomalie d'adhérence.",
     "", "", "En attente", "Normale"),
    ("13:45", "Anomalie de planning", "Signalement", "", "Signalement d'un problème de planning BT/BP.",
     "", "", "En attente", "Normale"),
    ("15:10", "Communication avec un manager", "Action réalisée", "", "Transmission d'une anomalie au manager.",
     "Transmission de l'anomalie", "Manager", "Résolu", "Normale"),
]


def demo_events(day=None):
    day = day or storage.today()
    out = []
    for i, (h, cat, nat, ag, desc, act, inf, stat, prio) in enumerate(_ROWS, 1):
        out.append({"id": f"demo{day:%y%m%d}{i:02d}", "date": day.isoformat(), "heure": h,
                    "saisi_le": f"{day.isoformat()} {h}:30", "agent": ag, "activite": "MVola Appel entrant",
                    "categorie": cat, "nature": nat, "description": desc, "action_vigie": act,
                    "informe": inf, "statut": stat, "priorite": prio, "observations": "", "historique": []})
    return out
