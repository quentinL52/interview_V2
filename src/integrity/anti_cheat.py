"""Anti-triche basique mais efficace — 100 % local (0 token LLM).

Non prioritaire pour le MVP, mais différenciant : un entretien IA naïf se
laisse berner par des réponses collées d'un LLM. Ici, des heuristiques
purement statistiques (pas de modèle lourd) lèvent des drapeaux :

- **burstiness** faible (longueurs de phrases trop uniformes) -> texte machine ;
- **diversité lexicale** anormale ;
- **écart de style CV vs entretien** (lisibilité, richesse) -> réponses non rédigées
  par la même personne.

Principe directeur : on n'ACCUSE jamais. Un soupçon élevé **baisse la confiance**
(croisé avec D6), il ne pénalise pas le score. C'est une aide à la décision
humaine, pas un verdict.
"""

from __future__ import annotations

import re
import statistics
from typing import Dict, List

try:
    import textstat  # type: ignore

    _HAS_TEXTSTAT = True
except Exception:  # pragma: no cover
    _HAS_TEXTSTAT = False


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"[.!?\n]+", text or "") if s.strip()]


def _words(text: str) -> List[str]:
    return re.findall(r"\b\w+\b", (text or "").lower())


def _burstiness(text: str) -> float:
    """Variabilité des longueurs de phrases (écart-type / moyenne).

    Humain -> phrases de longueurs variées (burstiness élevée). Machine ->
    longueurs uniformes (burstiness faible).
    """
    lengths = [len(_words(s)) for s in _sentences(text)]
    if len(lengths) < 2:
        return 1.0
    mean = statistics.mean(lengths)
    if mean == 0:
        return 1.0
    return statistics.pstdev(lengths) / mean


def _lexical_diversity(text: str) -> float:
    words = _words(text)
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def _readability(text: str) -> float:
    if _HAS_TEXTSTAT and text.strip():
        try:
            return float(textstat.flesch_reading_ease(text))
        except Exception:
            return 50.0
    # Fallback grossier : phrases plus longues -> moins lisible.
    sents = _sentences(text)
    if not sents:
        return 50.0
    avg = statistics.mean(len(_words(s)) for s in sents)
    return max(0.0, 100.0 - avg * 3)


def analyze_integrity(cv_text: str, interview_text: str) -> Dict:
    """Produit un rapport d'intégrité non bloquant.

    Retour : {suspicion_score 0-100, flags[], raisons[], metrics{}}.
    """
    interview_text = interview_text or ""
    burstiness = _burstiness(interview_text)
    diversity = _lexical_diversity(interview_text)
    readability = _readability(interview_text)

    suspicion = 0
    raisons: List[str] = []
    flags: List[str] = []

    if len(_words(interview_text)) >= 40:  # éviter de juger un texte trop court
        if burstiness < 0.25:
            suspicion += 35
            flags.append("monotonie")
            raisons.append("Longueurs de phrases très uniformes (style possiblement généré).")
        if diversity < 0.35:
            suspicion += 15
            flags.append("vocabulaire_pauvre")
            raisons.append("Diversité lexicale faible.")

        if cv_text and len(_words(cv_text)) >= 40:
            cv_read = _readability(cv_text)
            if abs(readability - cv_read) > 35:
                suspicion += 25
                flags.append("ecart_style_cv")
                raisons.append("Écart de style notable entre le CV et les réponses.")

    suspicion = min(100, suspicion)
    return {
        "suspicion_score": suspicion,
        "flags": flags,
        "raisons": raisons,
        "metrics": {
            "burstiness": round(burstiness, 3),
            "lexical_diversity": round(diversity, 3),
            "readability": round(readability, 1),
        },
        "note": "Indicatif, non bloquant. Un score élevé abaisse la confiance, "
                "il ne constitue pas une accusation.",
    }
