"""État et progression de l'entretien — calculés depuis l'historique.

L'API est **sans état** (le backend renvoie tout l'historique à chaque tour).
La progression est donc dérivée du **nombre de questions déjà posées**, et non
d'un graphe persistant. C'est ce qui garantit structurellement l'**absence de
boucle** : on avance toujours selon le budget, jamais en attendant une réponse
« parfaite » (le défaut majeur de la v1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.core.constants import QUESTIONS_PER_AGENT

# Dimensions évaluées par phase : la dimension primaire de la phase + les
# dimensions transverses D5 (communication) et D6 (fiabilité), notées partout.
SECTION_DIMENSIONS = {
    "icebreaker": ["D3_trajectoire", "D5_communication", "D6_fiabilite"],
    "auditeur": ["D1_profondeur_technique", "D5_communication", "D6_fiabilite"],
    "enqueteur": ["D4_transferable", "D6_fiabilite", "D5_communication"],
    "stratege": ["D2_raisonnement", "D5_communication", "D6_fiabilite"],
    "projecteur": ["D3_trajectoire", "D5_communication", "D6_fiabilite"],
}

# Ordre fixe des phases (une seule conversation continue côté candidat).
SECTION_ORDER = ["icebreaker", "auditeur", "enqueteur", "stratege", "projecteur"]

# Bornes cumulées de questions par phase, ex. [3, 6, 8, 10, 11].
_CUMULATIVE: List[int] = []
_acc = 0
for _s in SECTION_ORDER:
    _acc += QUESTIONS_PER_AGENT[_s]
    _CUMULATIVE.append(_acc)

TOTAL_QUESTIONS = _CUMULATIVE[-1]


@dataclass
class Progress:
    """Position courante de l'entretien."""
    questions_asked: int            # nb de questions (assistant) déjà posées
    answers_given: int              # nb de réponses (user) déjà fournies
    section: str                    # phase de la PROCHAINE question
    index_in_section: int           # rang de la question dans la phase (0-based)
    is_first_turn: bool
    should_finalize: bool


def _section_for_question(q_index: int) -> tuple[str, int]:
    """Donne (section, index_dans_section) pour la q_index-ième question (0-based)."""
    prev = 0
    for section, bound in zip(SECTION_ORDER, _CUMULATIVE):
        if q_index < bound:
            return section, q_index - prev
        prev = bound
    # Au-delà du budget : reste sur la dernière phase.
    return SECTION_ORDER[-1], QUESTIONS_PER_AGENT[SECTION_ORDER[-1]] - 1


def compute_progress(messages: List[Dict[str, str]]) -> Progress:
    """Dérive la progression à partir de l'historique de messages.

    `messages` : liste de {role, content}. On ignore les messages 'system'.
    """
    convo = [m for m in (messages or []) if m.get("role") in ("user", "assistant")]
    questions_asked = sum(1 for m in convo if m.get("role") == "assistant")
    answers_given = sum(1 for m in convo if m.get("role") == "user")

    is_first_turn = questions_asked == 0 and answers_given == 0

    # Finalisation : toutes les questions posées ET la dernière a reçu réponse.
    should_finalize = answers_given >= TOTAL_QUESTIONS

    next_q_index = questions_asked
    section, index_in_section = _section_for_question(next_q_index)

    return Progress(
        questions_asked=questions_asked,
        answers_given=answers_given,
        section=section,
        index_in_section=index_in_section,
        is_first_turn=is_first_turn,
        should_finalize=should_finalize,
    )


@dataclass
class QAItem:
    """Une paire question/réponse, rattachée à sa phase."""
    section: str
    index_in_section: int
    question: str
    answer: str
    question_id: str
    dimensions: List[str] = field(default_factory=list)


def segment_qa(messages: List[Dict[str, str]]) -> List[QAItem]:
    """Découpe l'historique en paires (question Roni, réponse candidat).

    Chaque question assistant est appariée à la réponse user qui suit, et
    rattachée à sa phase via l'index de question. Sert à l'évaluation : on
    n'envoie au juge que les Q/R pertinentes pour chaque dimension.
    """
    convo = [m for m in (messages or []) if m.get("role") in ("user", "assistant")]
    items: List[QAItem] = []
    q_index = 0
    i = 0
    while i < len(convo):
        msg = convo[i]
        if msg.get("role") != "assistant":
            i += 1
            continue
        question = msg.get("content", "")
        answer = ""
        if i + 1 < len(convo) and convo[i + 1].get("role") == "user":
            answer = convo[i + 1].get("content", "")
            i += 2
        else:
            i += 1
        section, idx = _section_for_question(q_index)
        items.append(
            QAItem(
                section=section,
                index_in_section=idx,
                question=question,
                answer=answer,
                question_id=f"{section}_q{idx}",
                dimensions=SECTION_DIMENSIONS.get(section, []),
            )
        )
        q_index += 1
    return items
