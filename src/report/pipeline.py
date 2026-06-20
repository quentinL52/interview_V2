"""Pipeline de finalisation : transcript -> SimulationReportV2 (dict).

Enchaîne, dans l'ordre :
1. évaluation (juge froid) -> signaux ;
2. agrégation déterministe -> triplets D1-D6 ;
3. anti-triche local + croisement confiance ;
4. adéquation au poste (inclusive) + positionnement ;
5. forces/faiblesses justifiées + argument démo + validations profil ;
6. feedback candidat (1 appel LLM de mise en forme).

Seules les étapes 1 et 6 utilisent un LLM ; tout le reste est déterministe.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.graph.evaluator import evaluate_transcript
from src.integrity.anti_cheat import analyze_integrity
from src.report.candidate_feedback import generate_candidate_feedback
from src.report.recruiter_report import (
    apply_integrity_to_confidence,
    build_argument_demo,
    build_radar,
    derive_forces_faiblesses,
    derive_validations,
)
from src.scoring.adequation_poste import evaluer_adequation
from src.scoring.dimensions import aggregate_all
from src.scoring.positionnement import positionner
from src.schemas.context_schema import InterviewContext
from src.schemas.report_schema import SimulationReportV2


def _cv_text(ctx: InterviewContext) -> str:
    p = ctx.profil
    parts: List[str] = []
    if p.introduction:
        parts.append(p.introduction)
    parts += [f"{s.nom} : {s.contexte}" for s in p.hard_skills]
    parts += [f"{s.nom} : {s.contexte}" for s in p.soft_skills]
    return " ".join(parts)


def _interview_text(messages: List[Dict[str, str]]) -> str:
    return " ".join(
        m.get("content", "") for m in (messages or []) if m.get("role") == "user"
    )


def build_final_result(
    ctx: InterviewContext, messages: List[Dict[str, str]]
) -> Dict[str, Any]:
    """Construit le rapport final complet (dict prêt à sérialiser)."""
    # 1-2. Évaluation -> triplets déterministes.
    signals = evaluate_transcript(messages)
    dimensions = aggregate_all(signals)

    # 3. Anti-triche (local) + croisement avec la confiance (jamais le score).
    integrite = analyze_integrity(_cv_text(ctx), _interview_text(messages))
    apply_integrity_to_confidence(dimensions, integrite)

    # 4. Adéquation inclusive + positionnement.
    adequation = evaluer_adequation(ctx, dimensions)
    positionnement = positionner(ctx, dimensions, adequation)

    # 5. Lecture recruteur justifiée.
    forces, faiblesses = derive_forces_faiblesses(dimensions)
    argument_demo = build_argument_demo(ctx, dimensions, adequation)
    validations = derive_validations(ctx, dimensions)
    radar = build_radar(dimensions)

    # 6. Feedback candidat (1 appel LLM de mise en forme).
    feedback = generate_candidate_feedback(ctx.profil.first_name, forces, faiblesses)

    report = SimulationReportV2(
        dimensions=dimensions,
        adequation=adequation,
        positionnement=positionnement,
        forces=forces,
        faiblesses=faiblesses,
        argument_demo=argument_demo,
        integrite=integrite,
        feedback_candidat=feedback,
        radar_candidat=radar,
        validations_skills=validations,
    )
    return report.model_dump()
