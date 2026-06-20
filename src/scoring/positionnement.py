"""Positionnement — AIRH ne tranche pas, il situe.

Remplace le GO/NO GO par `pret_pour` / `pas_encore_pour` + conditions de
réussite, calculé par des règles explicites à partir des dimensions, de
l'adéquation et de la séniorité visée. 100 % déterministe et explicable.

Esprit inclusif : une D1 modeste n'exclut pas si D3 (apprentissage) est forte
— on propose alors le poste junior avec un cadre d'accompagnement.
"""

from __future__ import annotations

from typing import List, Optional

from src.schemas.context_schema import InterviewContext
from src.schemas.report_schema import Adequation, Positionnement
from src.schemas.signals_schema import DimensionScore


def _dim(scores: List[DimensionScore], dim: str) -> Optional[DimensionScore]:
    return next((d for d in scores if d.dimension == dim), None)


def _score(scores: List[DimensionScore], dim: str) -> int:
    d = _dim(scores, dim)
    return d.score if d else 0


def _base_role(ctx: InterviewContext) -> str:
    return (
        ctx.profil.metier_cible
        or ctx.attendus.poste
        or "un poste data/IA"
    )


def _profil_resume(ctx: InterviewContext, scores: List[DimensionScore]) -> str:
    d1 = _dim(scores, "D1_profondeur_technique")
    d2 = _dim(scores, "D2_raisonnement")
    d3 = _dim(scores, "D3_trajectoire")
    parts = []
    if ctx.profil.is_reconversion:
        parts.append("Profil en reconversion")
    else:
        parts.append("Profil")
    parts.append(f"orienté {_base_role(ctx)}")
    if d1:
        parts.append(f"D1={d1.score}/5 ({d1.confiance})")
    if d2:
        parts.append(f"D2={d2.score}/5")
    if d3:
        parts.append(f"D3={d3.score}/5")
    return ", ".join(parts) + "."


def positionner(
    ctx: InterviewContext,
    dimension_scores: List[DimensionScore],
    adequation: Adequation,
) -> Positionnement:
    d1 = _score(dimension_scores, "D1_profondeur_technique")
    d2 = _score(dimension_scores, "D2_raisonnement")
    d3 = _score(dimension_scores, "D3_trajectoire")

    role = _base_role(ctx)
    seniorite = ctx.attendus.seniorite
    n_non_couvert = len(adequation.non_couvert)
    n_couvert = len(adequation.couvert)

    pret: List[str] = []
    pas_encore: List[str] = []

    # Règles explicites (inclusives) :
    apprend_vite = d3 >= 4
    socle_technique = d1 >= 3
    socle_minimal = d1 >= 2

    if socle_technique and n_non_couvert <= 1:
        pret.append(f"{role} ({seniorite})")
    elif socle_minimal or apprend_vite:
        # Niveau junior accessible, surtout si la trajectoire est forte.
        pret.append(f"{role} junior")
        if not socle_technique:
            pas_encore.append(f"{role} confirmé/senior")
    else:
        pas_encore.append(f"{role} ({seniorite})")

    # Raisonnement fort -> ouvre des rôles orientés analyse/résolution.
    if d2 >= 4 and "analyst" not in role.lower():
        pret.append("rôles orientés analyse / résolution de problème")

    # Conditions de réussite.
    conditions = []
    if apprend_vite and not socle_technique:
        conditions.append(
            "environnement avec un référent senior les 6 premiers mois (la "
            "vitesse d'apprentissage compense le socle technique en construction)"
        )
    if n_non_couvert >= 2:
        manques = ", ".join(i.competence for i in adequation.non_couvert[:3])
        conditions.append(f"montée en compétence sur : {manques}")
    if not conditions:
        conditions.append("intégration standard ; profil aligné avec les attendus.")

    return Positionnement(
        profil_resume=_profil_resume(ctx, dimension_scores),
        pret_pour=pret or [f"{role} junior"],
        pas_encore_pour=pas_encore,
        conditions_de_reussite=" ; ".join(conditions),
    )
