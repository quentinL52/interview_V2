"""Constantes du simulateur v2 — budgets, anti-boucle, dimensions.

Aucune logique métier ici : uniquement des seuils et libellés partagés,
pour que le comportement (budget de questions, anti-boucle, dimensions)
soit lisible et testable au même endroit.
"""

# --- Budget de questions par agent (≈11 questions au total) ---
QUESTIONS_PER_AGENT = {
    "icebreaker": 3,
    "auditeur": 3,
    "enqueteur": 2,
    "stratege": 2,
    "projecteur": 1,
}

# --- Anti-boucle (corrige le défaut majeur de la v1) ---
# Nombre maximum de relances sur UNE question si la réponse est vague.
# Au-delà, on avance quoi qu'il arrive : l'absence de preuve est un signal
# neutre (baisse la confiance), jamais un motif de répéter la question.
MAX_RELANCES = 1

# Garde-fou global : cap dur sur le nombre total de tours candidat.
# Somme des questions (11) + relances possibles + marge de sécurité.
MAX_TOTAL_TURNS = 16

# --- Dimensions d'évaluation D1-D6 ---
DIMENSIONS = [
    "D1_profondeur_technique",
    "D2_raisonnement",
    "D3_trajectoire",
    "D4_transferable",
    "D5_communication",
    "D6_fiabilite",
]

# Libellés candidat (radar) — D6 et la confiance ne sont jamais exposés bruts.
DIMENSIONS_LABELS_CANDIDAT = {
    "D1_profondeur_technique": "Profondeur technique",
    "D2_raisonnement": "Résolution de problème",
    "D3_trajectoire": "Capacité d'apprentissage",
    "D4_transferable": "Compétences transférables",
    "D5_communication": "Clarté de communication",
}

# --- Calibration / anti-complaisance ---
# Si la moyenne d'un batch dépasse ce seuil, la grille est trop laxiste.
SEUIL_MOYENNE_ALERTE = 3.5

# --- Routage des axes d'entretien du parser vers les agents ---
AGENTS = ["icebreaker", "auditeur", "enqueteur", "stratege", "projecteur"]

# --- Niveaux de maîtrise dérivés (échelle parser v2) ---
NIVEAUX_MAITRISE = ["declare", "academique", "projet", "production"]

# --- Niveaux de certitude des compétences transférables ---
CERTITUDES = ["flou", "probable", "confirme"]
