"""Orchestrateur de l'entretien — point d'entrée appelé par l'API.

Modèle **sans état** (request/response), aligné sur le backend existant :
à chaque tour, on reçoit tout l'historique, on décide la prochaine phase à
partir du budget de questions, on génère UNE question, puis on rend la main.

Garanties :
- **anti-boucle** : la progression suit le budget (jamais l'attente d'une
  réponse parfaite) ; un garde-fou dur force la finalisation au-delà du cap ;
- **fluidité** : une seule conversation continue, le candidat ne perçoit pas
  les phases ;
- séparation stricte : la conversation ne note rien ; l'évaluation (juge froid
  + grilles déterministes) n'a lieu qu'à la finalisation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.context.interview_context import build_interview_context
from src.core.constants import MAX_TOTAL_TURNS
from src.graph.agents import generate_question
from src.graph.state import TOTAL_QUESTIONS, compute_progress

logger = logging.getLogger(__name__)

_CLOSING = (
    "Merci {first_name} pour cet échange, c'était un vrai plaisir d'explorer ton "
    "parcours avec toi. Je prépare maintenant ton bilan et tes pistes de "
    "progression — tu vas pouvoir les consulter dans un instant."
)


class InterviewProcessor:
    """Pilote un tour d'entretien."""

    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload
        self.context = build_interview_context(
            payload.get("cv_document", {}), payload.get("job_offer")
        )

    # -- API principale ------------------------------------------------------ #

    def step(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Traite un tour : renvoie la prochaine question OU le bilan final."""
        convo = [m for m in (messages or []) if m.get("role") in ("user", "assistant")]
        progress = compute_progress(convo)

        # Garde-fou dur : au-delà du cap, on finalise quoi qu'il arrive.
        over_cap = len(convo) >= MAX_TOTAL_TURNS * 2

        if progress.should_finalize or over_cap:
            return self._finalize(convo)

        question = generate_question(
            self.context, progress.section, convo, progress.index_in_section
        )
        return {
            "response": question,
            "current_agent": progress.section,
            "status": "ongoing",
            "progress": {
                "questions_asked": progress.questions_asked + 1,
                "total_questions": TOTAL_QUESTIONS,
            },
        }

    # -- Finalisation -------------------------------------------------------- #

    def _finalize(self, convo: List[Dict[str, str]]) -> Dict[str, Any]:
        """Lance l'évaluation déterministe et construit le bilan.

        Import paresseux : la chaîne d'évaluation/rapport (juge froid, grilles,
        rapports) n'est nécessaire qu'ici, et reste découplée de la conversation.
        """
        first_name = self.context.profil.first_name
        closing = _CLOSING.format(first_name=first_name)

        try:
            from src.report.pipeline import build_final_result

            report = build_final_result(self.context, convo)
        except Exception as exc:  # ne jamais casser l'expérience candidat
            logger.error("Échec de la finalisation : %s", exc, exc_info=True)
            report = {"error": "report_generation_failed"}

        return {
            "response": closing,
            "current_agent": "final",
            "status": "finished",
            "report": report,
        }
