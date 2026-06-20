"""Feedback candidat : 1 appel LLM de MISE EN FORME (le LLM ne décide rien).

Le contenu (force + axes) est déterminé en amont par les grilles. Le LLM ne
fait que le rédiger en « tu », chaleureux et actionnable. Un fallback templaté
garantit un feedback même sans LLM (et permet l'option 0 token).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from src.schemas.report_schema import PointJustifie

logger = logging.getLogger(__name__)

_PROMPT = (Path(__file__).resolve().parent.parent / "prompts" / "feedback_candidat.txt").read_text(
    encoding="utf-8"
)


def _axes_text(faiblesses: List[PointJustifie]) -> str:
    if not faiblesses:
        return "Aucun axe majeur — continue à consolider tes acquis par la pratique."
    return "\n".join(f"- {f.libelle} : {f.justification}" for f in faiblesses[:3])


def _force_text(forces: List[PointJustifie]) -> str:
    if not forces:
        return "Ta capacité à te prêter sincèrement à l'exercice."
    return f"{forces[0].libelle} : {forces[0].justification}"


def _fallback(first_name: str, forces: List[PointJustifie], faiblesses: List[PointJustifie]) -> str:
    parts = [f"{first_name}, merci pour cet entretien."]
    if forces:
        parts.append(f"Ton point fort : {forces[0].libelle.lower()} — {forces[0].justification}")
    if faiblesses:
        parts.append("Pour progresser :")
        for f in faiblesses[:3]:
            parts.append(f"• {f.libelle} — {f.justification}")
    parts.append("Continue à t'entraîner : chaque réponse plus concrète et plus "
                 "argumentée renforce ton profil.")
    return "\n".join(parts)


def generate_candidate_feedback(
    first_name: str,
    forces: List[PointJustifie],
    faiblesses: List[PointJustifie],
) -> str:
    """Rédige le feedback candidat (LLM), avec repli déterministe."""
    try:
        from langchain_core.messages import SystemMessage

        from src.core.config import feedback_llm

        prompt = _PROMPT.format(
            first_name=first_name,
            force=_force_text(forces),
            axes=_axes_text(faiblesses),
        )
        response = feedback_llm().invoke([SystemMessage(content=prompt)])
        text = (response.content or "").strip()
        return text or _fallback(first_name, forces, faiblesses)
    except Exception as exc:
        logger.warning("Feedback LLM indisponible (%s) — repli templaté.", exc)
        return _fallback(first_name, forces, faiblesses)
