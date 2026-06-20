"""Configuration LLM et runtime du simulateur v2.

Principe directeur : le LLM ne fait que (1) converser et (2) extraire des
signaux. Deux profils LLM :
- interviewer : chaleureux, adaptatif (temperature élevée) ;
- evaluator : juge froid, déterministe (temperature 0, sortie structurée).

Les imports `langchain_openai` sont paresseux pour que les couches sans LLM
(adapters, grilles, tests unitaires) s'importent sans dépendance lourde.
"""

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

INTERVIEWER_MODEL = os.getenv("INTERVIEWER_MODEL", "gpt-4o-mini")
EVALUATOR_MODEL = os.getenv("EVALUATOR_MODEL", "gpt-4o-mini")
FEEDBACK_MODEL = os.getenv("FEEDBACK_MODEL", "gpt-4o-mini")

INTERVIEWER_TEMPERATURE = float(os.getenv("INTERVIEWER_TEMPERATURE", "0.7"))
EVALUATOR_TEMPERATURE = 0.0  # juge froid — toujours déterministe
FEEDBACK_TEMPERATURE = float(os.getenv("FEEDBACK_TEMPERATURE", "0.3"))

# Chemin du référentiel métier (réutilise le metiers.json du parser).
DEFAULT_METIERS_PATH = os.getenv("METIERS_JSON_PATH", "")


def interviewer_llm():
    """LLM conversationnel (chaleureux)."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=INTERVIEWER_MODEL,
        temperature=INTERVIEWER_TEMPERATURE,
        api_key=OPENAI_API_KEY,
    )


def evaluator_llm():
    """LLM juge (froid, déterministe) — extrait des signaux, ne note jamais."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=EVALUATOR_MODEL,
        temperature=EVALUATOR_TEMPERATURE,
        api_key=OPENAI_API_KEY,
    )


def feedback_llm():
    """LLM de mise en forme du feedback candidat (ne décide rien, reformule)."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=FEEDBACK_MODEL,
        temperature=FEEDBACK_TEMPERATURE,
        api_key=OPENAI_API_KEY,
    )
