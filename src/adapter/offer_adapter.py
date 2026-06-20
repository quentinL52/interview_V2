"""Adapter offre : `JobOffer` (backend) -> `AttendusPoste`.

L'offre arrive avec `competences` sous forme de **string** libre : on la
découpe en liste normalisée. On dérive aussi la **séniorité** (junior /
confirme / senior) à partir de signaux textuels de l'intitulé et de la
description — utile pour l'adéquation poste, sans jamais devenir un filtre
éliminatoire (la séniorité oriente les attentes, elle n'élimine personne).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

from src.schemas.context_schema import AttendusPoste

# Séparateurs courants dans un champ "compétences" libre.
_SPLIT_RE = re.compile(r"[,;/•·\n\t]| - |•")

_JUNIOR_HINTS = ("junior", "débutant", "debutant", "stage", "stagiaire", "alternance",
                 "apprenti", "0-2 ans", "première expérience", "premiere experience")
_SENIOR_HINTS = ("senior", "confirmé", "confirme", "lead", "principal", "expert",
                 "5 ans", "6 ans", "7 ans", "8 ans", "10 ans", "architecte", "head of")


def _norm(text: Optional[str]) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().strip()


def _split_competences(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    parts = _SPLIT_RE.split(raw)
    seen = set()
    result = []
    for part in parts:
        cleaned = part.strip(" .-— ")
        if not cleaned or len(cleaned) < 2:
            continue
        key = _norm(cleaned)
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _derive_seniorite(*texts: str) -> str:
    blob = " ".join(_norm(t) for t in texts if t)
    if any(h in blob for h in _SENIOR_HINTS):
        return "senior"
    if any(h in blob for h in _JUNIOR_HINTS):
        return "junior"
    return "confirme"


def adapt_offer(job_offer: Optional[Dict[str, Any]]) -> AttendusPoste:
    """Transforme une offre (dict) en `AttendusPoste`.

    Tolérant : une offre absente/incomplète produit un `AttendusPoste` vide
    (`is_fournie == False`), et le simulateur retombera sur le référentiel
    métier générique.
    """
    job_offer = job_offer or {}

    poste = job_offer.get("poste")
    mission = job_offer.get("mission")
    profil = job_offer.get("profil_recherche")
    description = (
        job_offer.get("description_nettoyee")
        or job_offer.get("description_poste")
        or ""
    )
    competences = _split_competences(job_offer.get("competences"))

    contexte_brut = " ".join(
        t for t in [poste, mission, profil, description] if t
    ).strip()

    return AttendusPoste(
        entreprise=job_offer.get("entreprise"),
        poste=poste,
        ville=job_offer.get("ville"),
        contrat=job_offer.get("contrat"),
        pole=job_offer.get("pole"),
        mission=mission,
        profil_recherche=profil,
        competences_attendues=competences,
        seniorite=_derive_seniorite(poste or "", profil or "", description),
        contexte_brut=contexte_brut[:4000],
    )
