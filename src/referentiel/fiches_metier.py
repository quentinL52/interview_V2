"""Logique métier data/IA : scénarios de mise en situation + compétences critiques.

Complète le référentiel `metiers.json` (descriptif) par la **logique métier**
qu'un LLM grand public n'a pas : des scénarios SJT réalistes par famille de
métier (avec une contrainte ajoutée pour tester l'adaptation — D2), et la
sélection des compétences critiques d'un poste.

C'est la spécialisation data/IA d'AIRH : analyst ≠ engineer ≠ ML.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

from src.schemas.context_schema import AttendusPoste, FicheMetier


def _norm(text: Optional[str]) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


@dataclass
class SJTScenario:
    """Scénario de mise en situation (mesure D2 — raisonnement)."""
    famille: str
    contexte: str          # situation initiale présentée au candidat
    contrainte_ajoutee: str  # twist introduit en cours pour tester l'adaptation
    competences_visees: List[str] = field(default_factory=list)


# Familles de métiers data/IA et leurs scénarios.
_SCENARIOS = {
    "analyst": SJTScenario(
        famille="analyst",
        contexte=(
            "Un responsable métier te dit que le chiffre d'affaires affiché sur "
            "son dashboard ne correspond pas à ce qu'il a en tête, et il te "
            "demande de corriger 'le bug' avant une réunion dans 1 heure."
        ),
        contrainte_ajoutee=(
            "En creusant, tu t'aperçois que les deux chiffres sont en fait "
            "calculés sur des périmètres différents (TTC vs HT). Comment tu gères ?"
        ),
        competences_visees=["SQL", "rigueur analytique", "communication métier"],
    ),
    "engineer": SJTScenario(
        famille="engineer",
        contexte=(
            "Un pipeline de données en production a échoué cette nuit, les "
            "tableaux de bord du matin sont vides et l'équipe métier s'impatiente."
        ),
        contrainte_ajoutee=(
            "Tu découvres que le volume de données a été multiplié par 10 du jour "
            "au lendemain et fait exploser le job. Quelle est ta démarche ?"
        ),
        competences_visees=["debugging", "architecture data", "gestion d'incident"],
    ),
    "ml": SJTScenario(
        famille="ml",
        contexte=(
            "Un modèle de prédiction que tu as mis en production voit ses "
            "performances se dégrader depuis deux semaines, sans changement de code."
        ),
        contrainte_ajoutee=(
            "Tu constates que la distribution des données d'entrée a changé "
            "(data drift). Comment tu investigues et que proposes-tu ?"
        ),
        competences_visees=["ML en production", "data drift", "méthode de diagnostic"],
    ),
    "generique": SJTScenario(
        famille="generique",
        contexte=(
            "On te confie un jeu de données inconnu et mal documenté, et on te "
            "demande d'en tirer une première analyse exploitable rapidement."
        ),
        contrainte_ajoutee=(
            "On t'annonce ensuite qu'une partie des données est incomplète et peu "
            "fiable. Comment adaptes-tu ta démarche ?"
        ),
        competences_visees=["raisonnement", "méthode", "gestion de l'incertitude"],
    ),
}

# Mots-clés -> famille de scénario.
_FAMILLE_HINTS = {
    "engineer": ("data engineer", "engineer data", "pipeline", "etl", "elt", "airflow",
                 "spark", "kafka", "dbt", "platform", "dataops"),
    "ml": ("machine learning", "ml engineer", "mlops", "deep learning", "data scientist",
           "modele", "modèle", "nlp", "computer vision", "llm", "ia engineer", "ai engineer"),
    "analyst": ("data analyst", "business intelligence", "bi analyst", "analytics",
                "analyste", "decisionnel", "décisionnel", "reporting"),
}


def famille_metier(metier_cible: Optional[str], attendus: AttendusPoste,
                   fiche: Optional[FicheMetier]) -> str:
    """Détermine la famille de scénario (analyst/engineer/ml/generique)."""
    blob = " ".join(
        _norm(x) for x in [
            metier_cible, attendus.poste, attendus.pole,
            fiche.nom if fiche else None, fiche.categorie if fiche else None,
        ] if x
    )
    # Ordre : ML et engineer avant analyst (plus spécifiques).
    for famille in ("ml", "engineer", "analyst"):
        if any(h in blob for h in _FAMILLE_HINTS[famille]):
            return famille
    return "generique"


def get_sjt_scenario(metier_cible: Optional[str], attendus: AttendusPoste,
                     fiche: Optional[FicheMetier]) -> SJTScenario:
    """Renvoie le scénario de mise en situation adapté au métier visé."""
    return _SCENARIOS[famille_metier(metier_cible, attendus, fiche)]


def critical_skills(attendus: AttendusPoste, fiche: Optional[FicheMetier]) -> List[str]:
    """Compétences critiques du poste : priorité à l'offre, complétée par la fiche.

    L'offre prime (attendus réels) ; la fiche métier complète quand l'offre est
    pauvre. On ne renvoie jamais une liste vide si une fiche existe.
    """
    skills: List[str] = list(attendus.competences_attendues)
    if fiche:
        for comp in fiche.competences_techniques:
            if comp not in skills:
                skills.append(comp)
    return skills
