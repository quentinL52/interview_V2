"""Schéma de sortie final : `SimulationReportV2`.

Tout est justifié et auditable : chaque force/faiblesse et chaque item
d'adéquation porte sa justification (preuve), conformément à la vision AIRH
(explicabilité, AI Act) et à l'usage démo entreprise.
"""

from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field

from src.schemas.signals_schema import DimensionScore


class AdequationItem(BaseModel):
    competence: str
    statut: str                      # couvert | a_developper | compense | non_couvert
    justification: str = ""


class Adequation(BaseModel):
    """Confrontation inclusive CV/entretien ↔ attendus du poste."""
    couvert: List[AdequationItem] = Field(default_factory=list)
    a_developper: List[AdequationItem] = Field(default_factory=list)
    compense_par: List[AdequationItem] = Field(default_factory=list)
    non_couvert: List[AdequationItem] = Field(default_factory=list)


class Positionnement(BaseModel):
    """AIRH ne rend pas un verdict : il positionne."""
    profil_resume: str = ""
    pret_pour: List[str] = Field(default_factory=list)
    pas_encore_pour: List[str] = Field(default_factory=list)
    conditions_de_reussite: str = ""


class PointJustifie(BaseModel):
    libelle: str
    justification: str = ""
    dimension: str = ""


class ValidationSkill(BaseModel):
    """Trace pour le profil dynamique (chantier 1) : skill validé en entretien."""
    skill: str
    niveau_cv: str
    source: str = "entretien"
    confiance: str = "faible"
    preuve_ref: str = ""


class SimulationReportV2(BaseModel):
    # Cœur évaluatif
    dimensions: List[DimensionScore] = Field(default_factory=list)
    adequation: Adequation = Field(default_factory=Adequation)
    positionnement: Positionnement = Field(default_factory=Positionnement)

    # Lecture recruteur (justifiée)
    forces: List[PointJustifie] = Field(default_factory=list)
    faiblesses: List[PointJustifie] = Field(default_factory=list)
    argument_demo: str = ""          # pourquoi ce candidat peut surperformer un profil filtré ATS
    integrite: Dict = Field(default_factory=dict)  # flags anti-triche (non bloquant)

    # Lecture candidat
    feedback_candidat: str = ""
    radar_candidat: Dict[str, int] = Field(default_factory=dict)  # D1-D5 (libellés candidat)

    # Boucle profil (chantier 1)
    validations_skills: List[ValidationSkill] = Field(default_factory=list)
