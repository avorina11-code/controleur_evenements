# VIGIE LOGBOOK

Journal de bord opérationnel de la vigie : enregistrer, horodater, classer, rechercher et reconstituer
tous les événements d'une journée. Stockage 100 % local en JSON, sans serveur SQL.

## Installation

Prérequis : Python 3.9 ou plus récent.

```bash
cd vigie_logbook
python -m venv .venv
# Windows :  .venv\Scripts\activate        Linux/macOS :  source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

L'application s'ouvre dans le navigateur (http://localhost:8501). Pour la lancer sur un autre port :
`streamlit run app.py --server.port 8600`.

## Structure

```
vigie_logbook/
├── app.py                 # pages et navigation
├── requirements.txt
├── .streamlit/config.toml # thème bleu nuit
├── vigie/
│   ├── constants.py       # catégories, statuts, priorités, boutons rapides
│   ├── storage.py         # JSON atomique, sauvegardes, validation, fusion, corbeille
│   ├── analysis.py        # DataFrame, filtres, recherche, indicateurs
│   ├── reports.py         # Excel, CSV, PDF journalier
│   ├── ui.py              # CSS, horloge + raccourcis JavaScript, timeline, formulaires
│   └── demo.py            # données de démonstration
└── data/
    ├── logbook.json       # vos données (créé automatiquement)
    └── backups/           # sauvegardes automatiques horodatées
```

## Utilisation rapide

1. **Saisie & chronologie** : cliquez un bouton rapide (Retard, PC KO, OSTIE…), tapez la description,
   `Ctrl+Entrée`. `Alt+N` place le curseur dans « Description ».
2. L'heure de l'événement est celle de l'enregistrement, sauf si vous ouvrez « Événement antérieur »
   pour saisir l'heure réelle. L'heure de saisie est toujours conservée à part.
3. Chaque carte peut être **modifiée** (historique des modifications conservé), marquée **Résolue**,
   ou supprimée (elle va dans la corbeille, récupérable).
4. **Nature** distingue un *signalement* (on vous informe), un *fait constaté* (vous l'avez vu) et une
   *action réalisée* (vous l'avez faite).
5. **Données & sauvegardes** : export JSON / Excel / CSV / PDF, import par fusion, restauration.

## Fiabilité

- Écriture atomique (fichier temporaire puis remplacement) : pas de fichier à moitié écrit.
- Sauvegarde automatique dans `data/backups/` (au plus toutes les 2 minutes, 200 conservées),
  et systématique avant import, restauration ou démo.
- Fichier corrompu au démarrage : copié en `logbook_CORROMPU_…json`, puis dernière sauvegarde valide restaurée.
- Import : structure validée, doublons détectés par identifiant, **jamais d'écrasement**.

## Format JSON

```json
{"application": "VIGIE LOGBOOK", "version": 1,
 "events": [{"id": "a1b2c3d4e5f6", "date": "2026-11-18", "heure": "08:12", "saisi_le": "2026-11-18 08:14:03",
             "agent": "Rakoto", "activite": "MVola Appel entrant", "categorie": "Problème informatique",
             "nature": "Signalement", "description": "PC ne démarre pas", "action_vigie": "", "informe": "",
             "statut": "En attente", "priorite": "Normale", "observations": "", "historique": []}],
 "corbeille": []}
```
Champs obligatoires à l'import : `id`, `date` (AAAA-MM-JJ), `heure` (HH:MM), `categorie`.
