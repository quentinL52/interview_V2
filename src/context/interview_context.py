"""Fusion du contexte d'entretien : profil + attendus + fiche métier.

Point d'entrée unique appelé par le graph. Produit l'`InterviewContext` et,
au passage, **enrichit le profil** de deux marqueurs essentiels au cœur AIRH :

1. `critique_offre` sur chaque skill candidat présent dans les attendus de
   l'offre -> l'auditeur priorisera ces compétences.
2. `skills_critiques` : compétences attendues (offre + fiche métier) que le
   candidat n'a PAS prouvées en projet/prod -> ce sont les zones à creuser,
   sans jamais éliminer (un manque pourra être compensé par D2/D3/D4).
"""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, List, Optional

from src.adapter.cv_adapter import adapt_cv
from src.adapter.offer_adapter import adapt_offer
from src.referentiel.metiers_loader import get_referentiel
from src.schemas.context_schema import (
    AttendusPoste,
    FicheMetier,
    InterviewContext,
    ProfilCandidat,
)


def _norm(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def _skill_match(skill_nom: str, attendu: str) -> bool:
    """Vrai si une compétence candidate correspond à un attendu (inclusion).

    Tolérant : "PostgreSQL" matche l'attendu "SQL / bases relationnelles".
    """
    s, a = _norm(skill_nom), _norm(attendu)
    if not s or not a:
        return False
    return s in a or a in s or any(tok in a for tok in s.split() if len(tok) > 2)


def _seniorite_keywords(fiche: Optional[FicheMetier], attendus: AttendusPoste) -> List[str]:
    """Compétences critiques de référence (fiche métier), repli si offre pauvre."""
    if fiche and fiche.competences_techniques:
        return list(fiche.competences_techniques)
    return list(attendus.competences_attendues)


def build_interview_context(
    cv_document: Dict[str, Any], job_offer: Optional[Dict[str, Any]]
) -> InterviewContext:
    """Construit le contexte fusionné consommé par le graph d'entretien."""
    profil: ProfilCandidat = adapt_cv(cv_document)
    attendus: AttendusPoste = adapt_offer(job_offer)

    referentiel = get_referentiel()
    fiche = referentiel.resolve(profil.metier_cible, attendus.poste)

    # 1) Marquer les compétences du candidat attendues par l'offre.
    attendus_norm = attendus.competences_attendues
    for skill in profil.hard_skills:
        if any(_skill_match(skill.nom, att) for att in attendus_norm):
            skill.critique_offre = True
            # Une compétence critique non éprouvée devient prioritaire à valider.
            if skill.niveau_maitrise in ("declare", "academique"):
                skill.a_valider_entretien = True

    # 2) Skills critiques attendus que le candidat n'a pas prouvés.
    prouves = {
        _norm(s.nom)
        for s in profil.hard_skills
        if s.niveau_maitrise in ("projet", "production")
    }
    reference = _seniorite_keywords(fiche, attendus)
    skills_critiques: List[str] = []
    for att in reference:
        if not any(_skill_match(p, att) for p in prouves):
            skills_critiques.append(att)

    return InterviewContext(
        profil=profil,
        attendus=attendus,
        fiche_metier=fiche,
        skills_critiques=skills_critiques,
    )
