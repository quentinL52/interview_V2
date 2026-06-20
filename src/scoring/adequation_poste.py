"""Adéquation au poste — confrontation INCLUSIVE des attendus de l'offre.

Cœur AIRH : on ne calcule pas un % de cases cochées. Pour chaque compétence
attendue, on classe :
- `couvert`      : prouvée (projet/prod sur le CV, cohérente en entretien) ;
- `a_developper` : présente mais peu éprouvée (académique/déclarée) ;
- `compense`     : absente/faible MAIS compensée par le raisonnement (D2),
                   la vitesse d'apprentissage (D3) ou un capital transférable
                   confirmé (D4) — c'est le candidat que l'ATS aurait jeté ;
- `non_couvert`  : absente et non compensée (signalé, jamais éliminatoire).

Chaque classement porte une justification. 100 % déterministe.
"""

from __future__ import annotations

import unicodedata
from typing import Dict, List, Optional

from src.referentiel.fiches_metier import critical_skills
from src.schemas.context_schema import InterviewContext
from src.schemas.report_schema import Adequation, AdequationItem
from src.schemas.signals_schema import DimensionScore


def _norm(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def _match(skill_nom: str, attendu: str) -> bool:
    s, a = _norm(skill_nom), _norm(attendu)
    if not s or not a:
        return False
    return s in a or a in s or any(tok in a for tok in s.split() if len(tok) > 2)


def _dim(scores: List[DimensionScore], dim: str) -> Optional[DimensionScore]:
    return next((d for d in scores if d.dimension == dim), None)


def _compensation(scores: List[DimensionScore], ctx: InterviewContext) -> Optional[str]:
    """Renvoie une justification de compensation si le profil compense un manque."""
    d2 = _dim(scores, "D2_raisonnement")
    d3 = _dim(scores, "D3_trajectoire")
    d4 = _dim(scores, "D4_transferable")

    raisons = []
    if d2 and d2.score >= 3:
        raisons.append(f"raisonnement solide (D2={d2.score}/5)")
    if d3 and d3.score >= 4:
        raisons.append(f"apprend vite (D3={d3.score}/5)")
    if d4 and d4.score >= 3:
        raisons.append(f"capital transférable confirmé (D4={d4.score}/5)")
    # Un transférable explicitement confirmé renforce la compensation.
    confirmes = [t.competence for t in ctx.profil.competences_transferables if t.certitude == "confirme"]
    if confirmes:
        raisons.append(f"expérience transférable : {', '.join(confirmes[:2])}")

    if not raisons:
        return None
    return "Manque compensable — " + ", ".join(raisons) + "."


def evaluer_adequation(
    ctx: InterviewContext, dimension_scores: List[DimensionScore]
) -> Adequation:
    """Construit l'adéquation au poste, inclusive et justifiée."""
    # Compétences candidat indexées par niveau de maîtrise.
    skills = ctx.profil.hard_skills
    prouves = {s.nom: s for s in skills if s.niveau_maitrise in ("projet", "production")}
    declares = {s.nom: s for s in skills if s.niveau_maitrise in ("declare", "academique")}

    d1 = _dim(dimension_scores, "D1_profondeur_technique")
    compensation = _compensation(dimension_scores, ctx)

    # Attendus : priorité à l'offre, complétés par la fiche métier.
    attendus = critical_skills(ctx.attendus, ctx.fiche_metier)

    adq = Adequation()
    deja_vu = set()
    for attendu in attendus:
        key = _norm(attendu)
        if key in deja_vu:
            continue
        deja_vu.add(key)

        matched_prouve = next((s for nom, s in prouves.items() if _match(nom, attendu)), None)
        matched_declare = next((s for nom, s in declares.items() if _match(nom, attendu)), None)

        if matched_prouve:
            justif = f"« {matched_prouve.nom} » éprouvée ({matched_prouve.niveau_maitrise})"
            if d1:
                justif += f", profondeur technique D1={d1.score}/5 ({d1.confiance})"
            adq.couvert.append(AdequationItem(competence=attendu, statut="couvert", justification=justif + "."))
        elif matched_declare:
            adq.a_developper.append(AdequationItem(
                competence=attendu, statut="a_developper",
                justification=f"« {matched_declare.nom} » présente mais peu éprouvée "
                              f"({matched_declare.niveau_maitrise}) — à consolider.",
            ))
        elif compensation:
            adq.compense_par.append(AdequationItem(
                competence=attendu, statut="compense", justification=compensation,
            ))
        else:
            adq.non_couvert.append(AdequationItem(
                competence=attendu, statut="non_couvert",
                justification="Non démontrée sur le CV ni en entretien — à explorer (non éliminatoire).",
            ))
    return adq
