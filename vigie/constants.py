"""Constantes métier de VIGIE LOGBOOK."""

CATEGORIES = {
    "Retard de connexion": "#D97706",
    "Absence non justifiée / constatée": "#B91C1C",
    "Problème informatique": "#7C3AED",
    "Demande / réclamation d'un agent": "#0891B2",
    "Départ OSTIE": "#2563EB",
    "Incident opérationnel": "#DC2626",
    "Basculement d'activité": "#0D9488",
    "Renfort d'effectif": "#16A34A",
    "Consigne managériale": "#1E3A8A",
    "Intervention de la vigie": "#475569",
    "Anomalie de planning": "#EA580C",
    "Problème d'adhérence": "#C026D3",
    "Communication avec un manager": "#0369A1",
    "Information RH": "#65A30D",
    "Autre événement": "#6B7280",
}

# Pour ne pas confondre un signalement, un fait constaté et une action réalisée.
NATURES = ["Signalement", "Fait constaté", "Action réalisée"]
NATURES_HELP = (
    "Signalement : quelqu'un vous informe d'un fait. "
    "Fait constaté : vous l'avez constaté vous-même. "
    "Action réalisée : une action que vous avez effectivement effectuée."
)

STATUTS = ["En attente", "En cours", "Résolu", "Sans suite", "Information"]
OPEN_STATUTS = ("En attente", "En cours")
STATUT_COLORS = {
    "En attente": "#D97706",
    "En cours": "#2563EB",
    "Résolu": "#16A34A",
    "Sans suite": "#B91C1C",
    "Information": "#64748B",
}

PRIORITES = ["Basse", "Normale", "Haute", "Critique"]
PRIORITE_COLORS = {"Basse": "#64748B", "Normale": "#2563EB", "Haute": "#EA580C", "Critique": "#DC2626"}

DEFAULT_ACTIVITY = "MVola Appel entrant"

# Catégories comptées comme « anomalies opérationnelles » dans le tableau de bord.
ANOMALIES = {"Incident opérationnel", "Anomalie de planning", "Problème d'adhérence"}
# Catégories listées dans la section « Anomalies » du rapport PDF.
REPORT_ANOMALIES = ANOMALIES | {"Problème informatique", "Absence non justifiée / constatée"}

QUICK_BUTTONS = [
    ("⏱ Retard", "Retard de connexion"),
    ("💻 PC KO", "Problème informatique"),
    ("☕ OSTIE", "Départ OSTIE"),
    ("🚫 Absence", "Absence non justifiée / constatée"),
    ("🔀 Basculement", "Basculement d'activité"),
    ("⚠ Incident", "Incident opérationnel"),
    ("📣 Consigne", "Consigne managériale"),
]
