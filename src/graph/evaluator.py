"""Évaluateur (juge froid) : transcript -> SignalUnit[].

Sépare strictement l'intervieweur (chaleureux) du juge (froid, temperature 0).
Le juge reçoit uniquement {question, réponse, indicateurs autorisés, ancres}
et renvoie des **indicateurs observés + verbatims**. Il n'attribue jamais de
score : les scores sont calculés par `scoring/grids.py`.

Optimisation tokens : une passe d'extraction par PHASE (≈5 appels), sans
l'historique conversationnel, en sortie structurée. Robuste à l'absence de LLM
(fallback neutre) pour ne jamais casser la finalisation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field

from src.graph.state import QAItem, segment_qa
from src.scoring.grids import anchors_for, indicators_for
from src.schemas.signals_schema import SignalUnit

logger = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_BASE = (_PROMPT_DIR / "evaluator_base.txt").read_text(encoding="utf-8")


# --- Schéma de sortie structurée du juge ---------------------------------- #

class DimensionSignal(BaseModel):
    dimension: str = Field(description="Identifiant de la dimension, ex. D1_profondeur_technique")
    indicateurs_presents: List[str] = Field(
        default_factory=list,
        description="Noms EXACTS des indicateurs démontrés, parmi la liste autorisée.",
    )
    reponse_generique: bool = False
    hors_sujet: bool = False
    verbatim: str = ""
    absence_note: str = ""


class QuestionEval(BaseModel):
    question_id: str
    signals: List[DimensionSignal] = Field(default_factory=list)


class PhaseExtraction(BaseModel):
    evaluations: List[QuestionEval] = Field(default_factory=list)


# --- Construction du prompt ----------------------------------------------- #

def _dimension_specs(dimensions: List[str]) -> str:
    blocks = []
    for dim in dimensions:
        inds = indicators_for(dim)
        anchors = anchors_for(dim)
        anchor_txt = "\n".join(f"    {lvl} : {txt}" for lvl, txt in anchors.items())
        blocks.append(
            f"• {dim}\n"
            f"  Indicateurs autorisés : {', '.join(inds)}\n"
            f"  Échelle de lecture (pour comprendre les indicateurs, NE PAS noter) :\n{anchor_txt}"
        )
    return "\n\n".join(blocks)


def _qa_block(items: List[QAItem]) -> str:
    lines = []
    for it in items:
        lines.append(
            f"[{it.question_id}]\n"
            f"  Question : {it.question}\n"
            f"  Réponse  : {it.answer or '(pas de réponse)'}"
        )
    return "\n\n".join(lines)


def _allowed(dim: str) -> set:
    return set(indicators_for(dim))


# --- Évaluation d'une phase ----------------------------------------------- #

def evaluate_phase(section_dimensions: List[str], items: List[QAItem]) -> List[SignalUnit]:
    """Évalue les Q/R d'une phase sur les dimensions données."""
    if not items:
        return []

    from src.core.config import evaluator_llm

    prompt = _BASE.format(
        dimension_specs=_dimension_specs(section_dimensions),
        qa_block=_qa_block(items),
    )

    try:
        llm = evaluator_llm().with_structured_output(PhaseExtraction)
        from langchain_core.messages import SystemMessage

        extraction: PhaseExtraction = llm.invoke([SystemMessage(content=prompt)])
    except Exception as exc:
        logger.error("Évaluateur indisponible (%s) — signaux neutres.", exc)
        return _neutral_signals(section_dimensions, items)

    return _to_signal_units(extraction, items)


def _to_signal_units(extraction: PhaseExtraction, items: List[QAItem]) -> List[SignalUnit]:
    """Convertit la sortie du juge en SignalUnit, en filtrant les indicateurs."""
    by_qid = {it.question_id: it for it in items}
    units: List[SignalUnit] = []
    for qeval in extraction.evaluations:
        item = by_qid.get(qeval.question_id)
        for sig in qeval.signals:
            allowed = _allowed(sig.dimension) if sig.dimension in _ALL_DIMS else set()
            if not allowed:
                continue
            indicators = {
                name: True for name in sig.indicateurs_presents if name in allowed
            }
            units.append(
                SignalUnit(
                    dimension=sig.dimension,
                    question_id=qeval.question_id,
                    indicators=indicators,
                    reponse_generique=bool(sig.reponse_generique),
                    hors_sujet=bool(sig.hors_sujet),
                    verbatim=sig.verbatim.strip(),
                    absence_note=sig.absence_note.strip(),
                )
            )
    return units


def _neutral_signals(dimensions: List[str], items: List[QAItem]) -> List[SignalUnit]:
    """Signaux vides (aucun indicateur) — score 0, confiance faible. Jamais punitif."""
    units = []
    for it in items:
        for dim in dimensions:
            units.append(
                SignalUnit(dimension=dim, question_id=it.question_id, indicators={})
            )
    return units


# --- Passe complète sur le transcript ------------------------------------- #

from src.core.constants import DIMENSIONS as _ALL_DIMS  # noqa: E402


def evaluate_transcript(messages: List[Dict[str, str]]) -> List[SignalUnit]:
    """Évalue tout l'entretien : segmente par phase puis évalue chaque phase."""
    items = segment_qa(messages)
    by_section: Dict[str, List[QAItem]] = {}
    for it in items:
        by_section.setdefault(it.section, []).append(it)

    all_units: List[SignalUnit] = []
    for section, sec_items in by_section.items():
        dims = sec_items[0].dimensions if sec_items else []
        all_units.extend(evaluate_phase(dims, sec_items))
    return all_units
