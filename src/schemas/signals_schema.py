"""Schémas des signaux extraits par l'évaluateur (juge froid).

Le LLM évaluateur ne renvoie QUE des `SignalUnit` : des indicateurs booléens
observables + un verbatim + ce qui manque. Il ne produit jamais de score.
Les scores (`DimensionScore`) sont calculés en Python par `scoring/`.

C'est la frontière stricte « le LLM observe, le code décide ».
"""

from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field


class Preuve(BaseModel):
    """Élément auditable justifiant un score (exigence AI Act Art. 13/14)."""
    type: str                       # "verbatim" | "absence"
    extrait: str = ""               # citation exacte du candidat
    note: str = ""                  # ce qui manquait, le cas échéant
    question_id: str = ""


class SignalUnit(BaseModel):
    """Signaux extraits pour UNE réponse, sur UNE dimension."""
    dimension: str
    question_id: str = ""
    indicators: Dict[str, bool] = Field(default_factory=dict)
    # Garde-fous anti-complaisance évalués par le juge (pas un score) :
    reponse_generique: bool = False  # récitable d'un blog -> ne compte pas comme preuve
    hors_sujet: bool = False         # réponse brillante mais à côté -> 0
    verbatim: str = ""               # citation candidate (preuve)
    absence_note: str = ""           # élément attendu et absent


class DimensionScore(BaseModel):
    """Triplet de sortie par dimension : score + confiance + preuves."""
    dimension: str
    score: int = 0                   # 0-5, calculé par les grilles
    confiance: str = "faible"        # haute | moyenne | faible (déterministe)
    preuves: List[Preuve] = Field(default_factory=list)
