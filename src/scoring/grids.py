"""Grilles de scoring à ancres — D1 à D6. 100 % déterministe, zéro LLM.

Chaque dimension définit :
- `INDICATORS` : les signaux booléens observables que l'évaluateur doit extraire ;
- `ANCHORS`    : la description comportementale de chaque niveau 0-5 (injectée
                 dans le prompt de l'évaluateur ET reflétée par la fonction de score) ;
- `gate(...)`  : une fonction **à seuils cumulatifs** qui transforme les
                 indicateurs en score 0-5.

Choix d'architecture : des **seuils cumulatifs** (gates) plutôt qu'une simple
somme pondérée. C'est plus fidèle aux ancres ("3 = choix justifiés ET limites
ET un debug réel") et applique mécaniquement les règles dures :
- score par défaut = 0, on monte uniquement avec des preuves ;
- une réponse générique ou hors-sujet ne peut pas créditer ;
- le niveau 5 est verrouillé derrière des preuves de séniorité réelles.

Ces fonctions ne prennent JAMAIS de décision sémantique : elles ne font
qu'appliquer des règles arithmétiques sur des booléens fournis par le juge.
"""

from __future__ import annotations

from typing import Callable, Dict, List

# Type d'un dict d'indicateurs booléens.
Indicators = Dict[str, bool]


def _i(ind: Indicators, key: str) -> bool:
    return bool(ind.get(key, False))


def _blocked(ind: Indicators, reponse_generique: bool, hors_sujet: bool) -> bool:
    """Règles dures : hors-sujet ou réponse générique => aucun crédit (0)."""
    return hors_sujet or reponse_generique


# --------------------------------------------------------------------------- #
#  D1 — Profondeur technique validée
# --------------------------------------------------------------------------- #

D1_INDICATORS = [
    "decrit_usage",                 # "on utilisait X"
    "justifie_choix",               # explique POURQUOI ce choix
    "identifie_limites",            # connaît les limites/pièges
    "raconte_debug_reel",           # un problème réel résolu, raconté précisément
    "propose_alternatives",         # compare des alternatives sous contraintes
    "decisions_archi_production",   # décisions d'archi assumées en prod (senior)
    "fait_monter_autres",           # a formé/encadré d'autres (senior)
]

D1_ANCHORS = {
    0: "Ne peut rien dire au-delà du nom de l'outil.",
    1: "Décrit l'usage mais ne justifie aucun choix.",
    2: "Justifie au moins un choix sur un cas réel, sans recul sur les limites.",
    3: "Choix justifiés + limites identifiées + un debug réel raconté précisément.",
    4: "En plus : alternatives comparées, décisions argumentées sous contraintes.",
    5: "En plus : décisions d'architecture en production, ou a fait monter d'autres.",
}


def gate_d1(ind: Indicators, reponse_generique: bool = False, hors_sujet: bool = False) -> int:
    if _blocked(ind, reponse_generique, hors_sujet):
        return 0
    level = 0
    if _i(ind, "decrit_usage"):
        level = 1
    if _i(ind, "justifie_choix"):
        level = 2
    if _i(ind, "justifie_choix") and _i(ind, "identifie_limites") and _i(ind, "raconte_debug_reel"):
        level = 3
    if level >= 3 and _i(ind, "propose_alternatives"):
        level = 4
    if level >= 4 and (_i(ind, "decisions_archi_production") or _i(ind, "fait_monter_autres")):
        level = 5
    return level


# --------------------------------------------------------------------------- #
#  D2 — Raisonnement & résolution de problème (mise en situation / SJT)
# --------------------------------------------------------------------------- #

D2_INDICATORS = [
    "comprend_probleme",            # reformule/clarifie l'énoncé
    "demarche_structuree",          # décompose en étapes
    "pertinence_technique",         # la solution tient techniquement
    "gere_contrainte_ajoutee",      # s'adapte au twist en cours de route
    "admet_inconnu_avec_methode",   # dit ce qu'il ne sait pas + comment chercher
    "identifie_risques",            # anticipe risques / cas limites
]

D2_ANCHORS = {
    0: "Ne comprend pas le problème ou répond à côté.",
    1: "Comprend le problème mais ne propose pas de démarche.",
    2: "Démarche structurée mais solution peu pertinente techniquement.",
    3: "Démarche structurée + solution techniquement pertinente.",
    4: "En plus : gère une contrainte ajoutée en cours de route.",
    5: "En plus : anticipe les risques et/ou admet ses limites avec une méthode de recherche.",
}


def gate_d2(ind: Indicators, reponse_generique: bool = False, hors_sujet: bool = False) -> int:
    if _blocked(ind, reponse_generique, hors_sujet):
        return 0
    level = 0
    if _i(ind, "comprend_probleme"):
        level = 1
    if _i(ind, "demarche_structuree"):
        level = 2
    if _i(ind, "demarche_structuree") and _i(ind, "pertinence_technique"):
        level = 3
    if level >= 3 and _i(ind, "gere_contrainte_ajoutee"):
        level = 4
    if level >= 4 and (_i(ind, "identifie_risques") or _i(ind, "admet_inconnu_avec_methode")):
        level = 5
    return level


# --------------------------------------------------------------------------- #
#  D3 — Trajectoire d'apprentissage (cœur de la détection des atypiques)
# --------------------------------------------------------------------------- #

D3_INDICATORS = [
    "auto_formation_documentee",    # s'est formé seul, ressources précises
    "apprend_de_echecs",            # raconte un échec et ce qu'il en a tiré
    "projets_difficulte_croissante",# montée en complexité dans ses projets
    "methode_explicite",            # sait DÉCRIRE comment il apprend
    "delta_12_mois",               # progression mesurable sur ~1 an
    "prochaine_marche_claire",      # sait la compétence suivante à acquérir
]

D3_ANCHORS = {
    0: "Aucun élément sur sa façon d'apprendre.",
    1: "Mentionne s'être formé, sans méthode ni ressources.",
    2: "Auto-formation documentée (ressources précises).",
    3: "En plus : projets de difficulté croissante OU apprend explicitement de ses échecs.",
    4: "En plus : méthode d'apprentissage explicite + progression mesurable sur 12 mois.",
    5: "Progression remarquable (ex. zéro -> projets aboutis en peu de temps) avec méthode reproductible.",
}


def gate_d3(ind: Indicators, reponse_generique: bool = False, hors_sujet: bool = False) -> int:
    if _blocked(ind, reponse_generique, hors_sujet):
        return 0
    level = 0
    if _i(ind, "auto_formation_documentee") or _i(ind, "apprend_de_echecs"):
        level = 1
    if _i(ind, "auto_formation_documentee"):
        level = 2
    if level >= 2 and (_i(ind, "projets_difficulte_croissante") or _i(ind, "apprend_de_echecs")):
        level = 3
    if level >= 3 and _i(ind, "methode_explicite") and _i(ind, "delta_12_mois"):
        level = 4
    if level >= 4 and _i(ind, "prochaine_marche_claire"):
        level = 5
    return level


# --------------------------------------------------------------------------- #
#  D4 — Capital transférable (convertit le "probable" en "confirmé")
# --------------------------------------------------------------------------- #

D4_INDICATORS = [
    "situation_concrete",           # raconte une situation réelle (pas une généralité)
    "competence_identifiee",        # la compétence transférable est nommée clairement
    "applicabilite_tech_demontree", # fait le pont explicite vers le poste data/IA
    "exemple_chiffre",              # impact mesurable / chiffré
]

D4_ANCHORS = {
    0: "Ne sait pas illustrer la compétence transférable.",
    1: "Évoque la compétence de façon vague, sans situation.",
    2: "Situation concrète mais lien avec le poste tech faible.",
    3: "Situation concrète + applicabilité au poste démontrée.",
    4: "En plus : impact chiffré / exemple mesurable.",
    5: "Pont déjà réalisé concrètement vers la tech, applicabilité forte et directe.",
}


def gate_d4(ind: Indicators, reponse_generique: bool = False, hors_sujet: bool = False) -> int:
    if _blocked(ind, reponse_generique, hors_sujet):
        return 0
    level = 0
    if _i(ind, "competence_identifiee"):
        level = 1
    if _i(ind, "situation_concrete"):
        level = 2
    if _i(ind, "situation_concrete") and _i(ind, "applicabilite_tech_demontree"):
        level = 3
    if level >= 3 and _i(ind, "exemple_chiffre"):
        level = 4
    if level >= 4 and _i(ind, "applicabilite_tech_demontree") and _i(ind, "situation_concrete"):
        # niveau 5 = pont déjà réalisé : exige la combinaison la plus forte
        if _i(ind, "exemple_chiffre"):
            level = 5
    return level


def certitude_from_d4(score: int) -> str:
    """Convertit un score D4 en certitude de la compétence transférable.

    Cœur AIRH : l'entretien fait passer un transférable de 'probable' à
    'confirmé' dès qu'il est prouvé (score >= 3).
    """
    if score >= 4:
        return "confirme"
    if score >= 2:
        return "probable"
    return "flou"


# --------------------------------------------------------------------------- #
#  D5 — Communication technique (transverse, notée sur chaque réponse)
# --------------------------------------------------------------------------- #

D5_INDICATORS = [
    "reponse_structuree",           # plan clair, pas décousu
    "comprehensible",               # se comprend sans effort
    "vulgarise",                    # explique sans jargon inutile
    "synthetique",                  # va à l'essentiel, pas de digression
    "exemple_illustratif",          # illustre par un exemple
]

D5_ANCHORS = {
    0: "Réponse incompréhensible ou totalement décousue.",
    1: "Répond mais confus, difficile à suivre.",
    2: "Compréhensible avec effort.",
    3: "Clair et structuré.",
    4: "En plus : vulgarise bien, sans jargon inutile.",
    5: "En plus : synthétique et pédagogue (illustre, va à l'essentiel).",
}


def gate_d5(ind: Indicators, reponse_generique: bool = False, hors_sujet: bool = False) -> int:
    # D5 n'est pas bloquée par 'reponse_generique' (on évalue la forme),
    # mais un hors-sujet total reste 0.
    if hors_sujet:
        return 0
    level = 0
    if _i(ind, "comprehensible"):
        level = 2 if not _i(ind, "reponse_structuree") else 3
    elif _i(ind, "reponse_structuree"):
        level = 1
    if level >= 3 and _i(ind, "vulgarise"):
        level = 4
    if level >= 4 and _i(ind, "synthetique") and _i(ind, "exemple_illustratif"):
        level = 5
    return level


# --------------------------------------------------------------------------- #
#  D6 — Fiabilité professionnelle (honnêteté + constance CV/entretien)
# --------------------------------------------------------------------------- #

D6_INDICATORS = [
    "honnetete_intellectuelle",     # admet ne pas savoir plutôt que bluffer
    "coherence_reponses",           # ses réponses ne se contredisent pas
    "constance_cv_entretien",       # cohérent avec ce que dit le CV
    "lucidite_sur_soi",             # conscient de ses forces/limites
    # Signaux NÉGATIFS (plafonnent le score) :
    "bluff_detecte",                # invente / récite sans substance sur relance
    "ecart_cv_entretien",           # contredit le CV de façon notable
]

D6_ANCHORS = {
    0: "Bluff manifeste ou écarts majeurs avec le CV.",
    1: "Incohérences notables dans les réponses ou avec le CV.",
    2: "Quelques flottements, mais globalement de bonne foi.",
    3: "Honnête et cohérent avec son CV.",
    4: "En plus : admet clairement ses limites avec lucidité.",
    5: "En plus : grande rigueur, constance parfaite, lucidité remarquable sur soi.",
}


def gate_d6(ind: Indicators, reponse_generique: bool = False, hors_sujet: bool = False) -> int:
    # Signaux négatifs : ils plafonnent, sans jamais devenir une accusation
    # (l'anti-triche ne fait que baisser la confiance, voir scoring/dimensions).
    if _i(ind, "bluff_detecte") or _i(ind, "ecart_cv_entretien"):
        # au plus niveau 1 si un signal négatif fort est présent
        return 0 if (_i(ind, "bluff_detecte") and _i(ind, "ecart_cv_entretien")) else 1
    level = 0
    if _i(ind, "coherence_reponses") or _i(ind, "constance_cv_entretien"):
        level = 2
    if _i(ind, "coherence_reponses") and _i(ind, "constance_cv_entretien"):
        level = 3
    if level >= 3 and (_i(ind, "honnetete_intellectuelle") or _i(ind, "lucidite_sur_soi")):
        level = 4
    if level >= 4 and _i(ind, "honnetete_intellectuelle") and _i(ind, "lucidite_sur_soi"):
        level = 5
    return level


# --------------------------------------------------------------------------- #
#  Registre des grilles
# --------------------------------------------------------------------------- #

GateFn = Callable[..., int]

GRILLES: Dict[str, Dict] = {
    "D1_profondeur_technique": {"indicators": D1_INDICATORS, "anchors": D1_ANCHORS, "gate": gate_d1},
    "D2_raisonnement": {"indicators": D2_INDICATORS, "anchors": D2_ANCHORS, "gate": gate_d2},
    "D3_trajectoire": {"indicators": D3_INDICATORS, "anchors": D3_ANCHORS, "gate": gate_d3},
    "D4_transferable": {"indicators": D4_INDICATORS, "anchors": D4_ANCHORS, "gate": gate_d4},
    "D5_communication": {"indicators": D5_INDICATORS, "anchors": D5_ANCHORS, "gate": gate_d5},
    "D6_fiabilite": {"indicators": D6_INDICATORS, "anchors": D6_ANCHORS, "gate": gate_d6},
}


def score_signal(dimension: str, indicators: Indicators,
                 reponse_generique: bool = False, hors_sujet: bool = False) -> int:
    """Score 0-5 d'une réponse sur une dimension, via la grille à ancres."""
    grille = GRILLES.get(dimension)
    if not grille:
        raise KeyError(f"Dimension inconnue : {dimension}")
    return grille["gate"](indicators, reponse_generique, hors_sujet)


def indicators_for(dimension: str) -> List[str]:
    return GRILLES[dimension]["indicators"]


def anchors_for(dimension: str) -> Dict[int, str]:
    return GRILLES[dimension]["anchors"]
