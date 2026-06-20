"""Agrégation d'une dimension : SignalUnit[] -> DimensionScore.

Transforme les signaux extraits (plusieurs réponses) en un triplet
{score, confiance, preuves} déterministe.

- **score** : moyenne des scores par réponse (chacun via les grilles à ancres),
  arrondi de façon conservatrice (on n'arrondit jamais au-dessus à la moitié).
- **confiance** : fonction de la COUVERTURE (nb de réponses sur la dimension)
  et de la QUALITÉ des preuves (verbatims présents, peu d'évasif). Une faible
  confiance fait afficher « 3, à confirmer » plutôt qu'un faux 3 solide.
- **preuves** : verbatims et absences, horodatables (auditable, AI Act).

Aucune sémantique ici : uniquement de l'arithmétique sur les signaux du juge.
"""

from __future__ import annotations

import math
from typing import List

from src.scoring.grids import score_signal
from src.schemas.signals_schema import DimensionScore, Preuve, SignalUnit

# Couverture attendue par dimension (nb de réponses qui la ciblent en nominal).
# Sert uniquement au calcul de confiance, pas au score.
_COUVERTURE_ATTENDUE = {
    "D1_profondeur_technique": 3,
    "D2_raisonnement": 2,
    "D3_trajectoire": 2,
    "D4_transferable": 2,
    "D5_communication": 4,   # transverse : noté sur de nombreuses réponses
    "D6_fiabilite": 3,       # transverse également
}


def _conservative_round(value: float) -> int:
    """Arrondi conservateur : 2.5 -> 2 (le doute ne profite pas au score)."""
    floor = math.floor(value)
    return floor + 1 if (value - floor) > 0.5 else floor


def _confiance(dimension: str, units: List[SignalUnit], scores: List[int]) -> str:
    coverage = len(units)
    if coverage == 0:
        return "faible"

    attendue = _COUVERTURE_ATTENDUE.get(dimension, 2)
    # Part de réponses exploitables (ni évasives, ni hors-sujet).
    exploitables = [u for u in units if not (u.reponse_generique or u.hors_sujet)]
    ratio_exploitable = len(exploitables) / coverage if coverage else 0.0
    # Présence de verbatims concrets.
    verbatims = [u for u in units if u.verbatim.strip()]
    ratio_verbatim = len(verbatims) / coverage if coverage else 0.0

    if coverage >= attendue and ratio_exploitable >= 0.6 and ratio_verbatim >= 0.5:
        niveau = "haute"
    elif coverage >= max(1, attendue - 1) and ratio_exploitable >= 0.5:
        niveau = "moyenne"
    else:
        niveau = "faible"

    # Beaucoup d'évasif -> on descend d'un cran (anti-faux-positif).
    if ratio_exploitable < 0.5 and niveau == "haute":
        niveau = "moyenne"
    return niveau


def _preuves(units: List[SignalUnit]) -> List[Preuve]:
    preuves: List[Preuve] = []
    for u in units:
        if u.verbatim.strip():
            preuves.append(
                Preuve(type="verbatim", extrait=u.verbatim.strip(), question_id=u.question_id)
            )
        if u.absence_note.strip():
            preuves.append(
                Preuve(type="absence", note=u.absence_note.strip(), question_id=u.question_id)
            )
    return preuves


def aggregate_dimension(dimension: str, units: List[SignalUnit]) -> DimensionScore:
    """Calcule le triplet d'une dimension à partir de ses signaux."""
    units = [u for u in units if u.dimension == dimension]
    if not units:
        return DimensionScore(dimension=dimension, score=0, confiance="faible", preuves=[])

    scores = [
        score_signal(dimension, u.indicators, u.reponse_generique, u.hors_sujet)
        for u in units
    ]
    mean = sum(scores) / len(scores)
    final = _conservative_round(mean)

    return DimensionScore(
        dimension=dimension,
        score=max(0, min(5, final)),
        confiance=_confiance(dimension, units, scores),
        preuves=_preuves(units),
    )


def aggregate_all(units: List[SignalUnit]) -> List[DimensionScore]:
    """Agrège toutes les dimensions présentes dans les signaux."""
    from src.core.constants import DIMENSIONS

    return [aggregate_dimension(dim, units) for dim in DIMENSIONS]
