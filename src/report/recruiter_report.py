"""Construction déterministe des éléments du rapport recruteur.

Forces/faiblesses JUSTIFIÉES (chaque point ancré sur un verbatim ou une
absence), argument démo (« pourquoi ce candidat pourrait surperformer un profil
filtré par l'ATS »), et validations de compétences pour le profil dynamique.

Aucun LLM : tout dérive des triplets de dimensions et de l'adéquation.
"""

from __future__ import annotations

from typing import List, Optional

from src.core.constants import DIMENSIONS_LABELS_CANDIDAT
from src.schemas.context_schema import InterviewContext
from src.schemas.report_schema import (
    Adequation,
    PointJustifie,
    ValidationSkill,
)
from src.schemas.signals_schema import DimensionScore, Preuve

_LABELS = {
    "D1_profondeur_technique": "Profondeur technique",
    "D2_raisonnement": "Raisonnement & résolution de problème",
    "D3_trajectoire": "Trajectoire d'apprentissage",
    "D4_transferable": "Capital transférable",
    "D5_communication": "Communication technique",
    "D6_fiabilite": "Fiabilité professionnelle",
}


def _first_verbatim(preuves: List[Preuve]) -> Optional[str]:
    return next((p.extrait for p in preuves if p.type == "verbatim" and p.extrait), None)


def _first_absence(preuves: List[Preuve]) -> Optional[str]:
    return next((p.note for p in preuves if p.type == "absence" and p.note), None)


def derive_forces_faiblesses(
    dimensions: List[DimensionScore],
) -> tuple[List[PointJustifie], List[PointJustifie]]:
    forces: List[PointJustifie] = []
    faiblesses: List[PointJustifie] = []

    for d in dimensions:
        label = _LABELS.get(d.dimension, d.dimension)
        verbatim = _first_verbatim(d.preuves)
        absence = _first_absence(d.preuves)

        # Force : score élevé, idéalement confirmé par un verbatim.
        if d.score >= 4 or (d.score == 3 and d.confiance == "haute"):
            justif = f"{label} : {d.score}/5 (confiance {d.confiance})."
            if verbatim:
                justif += f" Ex. : « {verbatim} »"
            forces.append(PointJustifie(libelle=label, justification=justif, dimension=d.dimension))

        # Faiblesse : score bas OU confiance faible (info manquante).
        elif d.score <= 1:
            justif = f"{label} : {d.score}/5."
            if absence:
                justif += f" {absence}"
            faiblesses.append(PointJustifie(libelle=label, justification=justif, dimension=d.dimension))

    # Trier par sévérité / force.
    forces.sort(key=lambda p: p.libelle)
    return forces[:4], faiblesses[:4]


def build_argument_demo(
    ctx: InterviewContext,
    dimensions: List[DimensionScore],
    adequation: Adequation,
) -> str:
    """L'argument de vente : ce qu'un ATS aurait raté.

    Ne se déclenche que si le profil a une vraie raison d'être sous-estimé par
    un filtre classique (manques compensés + dimensions différenciantes).
    """
    d = {dim.dimension: dim for dim in dimensions}
    d2 = d.get("D2_raisonnement")
    d3 = d.get("D3_trajectoire")
    d4 = d.get("D4_transferable")

    differenciants = []
    if d2 and d2.score >= 3:
        differenciants.append(f"résout des problèmes inconnus avec méthode (D2={d2.score}/5)")
    if d3 and d3.score >= 4:
        differenciants.append(f"apprend vite et de façon structurée (D3={d3.score}/5)")
    if d4 and d4.score >= 3:
        differenciants.append(f"mobilise un capital transférable confirmé (D4={d4.score}/5)")

    if not (adequation.compense_par and differenciants):
        return ""

    manques = ", ".join(i.competence for i in (adequation.compense_par + adequation.non_couvert)[:3])
    parcours = "reconversion" if ctx.profil.is_reconversion else "parcours non linéaire"
    return (
        f"Un filtre ATS aurait probablement écarté ce profil ({parcours}) sur "
        f"l'absence de : {manques}. Or l'entretien montre qu'il "
        + ", ".join(differenciants)
        + ". C'est exactement le talent atypique que les critères rigides ratent."
    )


def derive_validations(
    ctx: InterviewContext, dimensions: List[DimensionScore]
) -> List[ValidationSkill]:
    """Trace pour le profil dynamique (chantier 1) : compétences critiques validées."""
    d1 = next((x for x in dimensions if x.dimension == "D1_profondeur_technique"), None)
    if not d1:
        return []
    preuve_ref = ""
    vb = _first_verbatim(d1.preuves)
    if vb:
        preuve_ref = vb[:160]

    validations = []
    for skill in ctx.profil.hard_skills:
        if skill.critique_offre and skill.niveau_maitrise in ("projet", "production"):
            validations.append(
                ValidationSkill(
                    skill=skill.nom,
                    niveau_cv=skill.niveau_maitrise,
                    source="entretien",
                    confiance=d1.confiance,
                    preuve_ref=preuve_ref,
                )
            )
    return validations


def build_radar(dimensions: List[DimensionScore]) -> dict:
    """Radar candidat : D1-D5 avec libellés candidat (D6/confiance jamais exposés)."""
    radar = {}
    by_dim = {d.dimension: d for d in dimensions}
    for dim, label in DIMENSIONS_LABELS_CANDIDAT.items():
        d = by_dim.get(dim)
        radar[label] = d.score if d else 0
    return radar


def apply_integrity_to_confidence(
    dimensions: List[DimensionScore], integrite: dict
) -> None:
    """Croise l'anti-triche avec D6 : un fort soupçon abaisse la confiance.

    Jamais le score — uniquement la confiance (pas d'accusation).
    """
    if integrite.get("suspicion_score", 0) < 50:
        return
    for d in dimensions:
        if d.dimension == "D6_fiabilite" and d.confiance == "haute":
            d.confiance = "moyenne"
