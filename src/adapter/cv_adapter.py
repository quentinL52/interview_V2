"""Adapter CV : `CVParsedFinal` (parser v1.5) -> `ProfilCandidat`.

Le parser v1.5 ne produit pas encore `niveau_maitrise`, `a_valider_entretien`
ni un `entretien_guide` structuré. Cet adapter les **dérive** à partir de ce
qui existe réellement (contexte des skills, technologies des projets,
`evaluation_roni` des expériences, `axes_entretien_simulateur`,
`soft_skills[].transferable`).

Objectif : aucune dépendance du simulateur au format exact du parser, et
compatibilité ascendante (si un `entretien_guide` structuré apparaît un jour,
on le détecte et on court-circuite les heuristiques).

Tout est tolérant aux champs manquants : un CV partiel ne doit jamais crasher.
"""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, List, Optional

from src.schemas.context_schema import (
    AxeEntretienPriorise,
    CompetenceTransferable,
    ProfilCandidat,
    ProjetResume,
    SkillEval,
    SoftSkillEval,
)

# Mots-clés signalant un usage purement académique/scolaire d'une compétence.
_ACADEMIC_HINTS = (
    "formation",
    "cours",
    "école",
    "ecole",
    "université",
    "universite",
    "licence",
    "master",
    "diplôme",
    "diplome",
    "bachelor",
    "scolaire",
    "académique",
    "academique",
    "td",
    "tp",
)

# Routage des axes d'entretien du parser vers le bon agent.
_AGENT_KEYWORDS = {
    "icebreaker": ("parcours", "motivation", "reconversion", "transition", "pourquoi"),
    "enqueteur": (
        "transfer", "transvers", "soft", "comportement", "gestion", "equipe",
        "équipe", "communication", "relation", "autonomie", "experience non",
    ),
    "stratege": ("situation", "probleme", "problème", "scenario", "scénario", "résoudre"),
    "projecteur": ("avenir", "projection", "apprentissage", "evolution", "évolution"),
}


def _norm(text: Optional[str]) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().strip()


def _route_agent(theme: str, competence: str) -> str:
    """Choisit l'agent destinataire d'un axe d'entretien.

    Défaut = auditeur (axe technique) : c'est le cas le plus fréquent et le
    moins risqué (la profondeur technique est toujours pertinente à creuser).
    """
    blob = _norm(theme) + " " + _norm(competence)
    for agent, keywords in _AGENT_KEYWORDS.items():
        if any(k in blob for k in keywords):
            return agent
    return "auditeur"


def _derive_niveau_maitrise(
    skill_nom: str, contexte: str, tech_projets: set, tech_exp: set
) -> str:
    """Dérive declare/academique/projet/production pour une compétence.

    Heuristique conservatrice : on ne sur-crédite jamais une compétence.
    - présente dans une expérience pro tech -> production
    - présente dans un projet -> projet
    - contexte scolaire/formation -> academique
    - sinon -> declare
    """
    key = _norm(skill_nom)
    if key and key in tech_exp:
        return "production"
    if key and key in tech_projets:
        return "projet"
    ctx = _norm(contexte)
    if any(h in ctx for h in _ACADEMIC_HINTS):
        return "academique"
    return "declare"


def _collect_project_techs(projets: List[Dict[str, Any]]) -> set:
    techs = set()
    for proj in projets or []:
        for tech in proj.get("technologies", []) or []:
            techs.add(_norm(tech))
    return techs


def _collect_tech_experience_terms(experiences: List[Dict[str, Any]]) -> set:
    """Termes issus des expériences marquées techniques par Roni.

    On ne dispose pas d'une liste de technos par expérience : on indexe les
    mots significatifs du poste + responsabilités des expériences `is_tech`,
    ce qui suffit à reconnaître une compétence utilisée en contexte pro.
    """
    terms = set()
    for exp in experiences or []:
        eval_roni = exp.get("evaluation_roni") or {}
        if not eval_roni.get("is_tech"):
            continue
        blob = " ".join(
            [exp.get("poste", "")] + (exp.get("responsabilites_brutes") or [])
        )
        for word in _norm(blob).replace("/", " ").replace(",", " ").split():
            if len(word) > 2:
                terms.add(word)
    return terms


def _build_transferables(
    soft_skills: List[Dict[str, Any]], experiences: List[Dict[str, Any]]
) -> List[CompetenceTransferable]:
    """Construit le capital transférable (D4) à confirmer en entretien.

    Sources :
    - soft_skills[].transferable (is_transferable=True) ;
    - expériences NON techniques bien valorisées par Roni (note_soft élevée).
    Côté CV, la certitude reste 'probable' au mieux : l'entretien la confirme.
    """
    result: List[CompetenceTransferable] = []

    for skill in soft_skills or []:
        transf = skill.get("transferable") or {}
        if not transf.get("is_transferable"):
            continue
        applicabilite = _norm(transf.get("applicabilite_tech", "moyenne"))
        certitude = "probable" if applicabilite in ("elevee", "élevée", "elevée") else "flou"
        result.append(
            CompetenceTransferable(
                source=skill.get("context", "") or "",
                competence=skill.get("skill", ""),
                certitude=certitude,
                applicabilite_tech=transf.get("applicabilite_tech", "moyenne"),
                note="Déclaré sur le CV — à confirmer en entretien.",
            )
        )

    for exp in experiences or []:
        eval_roni = exp.get("evaluation_roni") or {}
        if eval_roni.get("is_tech"):
            continue
        note_soft = eval_roni.get("note_soft_skills_valeur")
        if note_soft is not None and note_soft >= 6:
            result.append(
                CompetenceTransferable(
                    source=f"{exp.get('poste', '')} — {exp.get('entreprise', '')}".strip(" —"),
                    competence=f"Capital de l'expérience : {exp.get('poste', 'expérience')}",
                    certitude="probable",
                    applicabilite_tech="moyenne",
                    note=eval_roni.get("avis_roni", "")[:300],
                )
            )

    return result


def _build_axes(
    reco: Dict[str, Any], structured_guide: Optional[Dict[str, Any]]
) -> List[AxeEntretienPriorise]:
    """Construit les axes priorisés.

    Compatibilité ascendante : si un `entretien_guide` structuré par agent est
    présent (parser v2 futur), on l'utilise tel quel ; sinon on route la liste
    plate `axes_entretien_simulateur`.
    """
    axes: List[AxeEntretienPriorise] = []

    if structured_guide:
        for agent_key, bloc in structured_guide.items():
            agent = agent_key.replace("agent_", "")
            agent = {
                "parcours": "icebreaker",
                "competences_techniques": "auditeur",
                "transferable": "enqueteur",
                "soft_skills": "enqueteur",
            }.get(agent, agent if agent in _AGENT_KEYWORDS or agent == "auditeur" else "auditeur")
            for point in bloc.get("points", []) or []:
                axes.append(
                    AxeEntretienPriorise(
                        agent=agent,
                        theme=point.get("sujet", ""),
                        question_guide=point.get("question_guide", ""),
                        competence_ciblee=point.get("sujet", ""),
                        niveau_urgence=point.get("niveau_urgence", "moyenne"),
                    )
                )
        if axes:
            return axes

    for axe in reco.get("axes_entretien_simulateur", []) or []:
        theme = axe.get("theme", "")
        competence = axe.get("competence_ciblee", "")
        axes.append(
            AxeEntretienPriorise(
                agent=_route_agent(theme, competence),
                theme=theme,
                question_guide=axe.get("question_challenge", ""),
                competence_ciblee=competence,
                niveau_urgence="moyenne",
            )
        )
    return axes


def adapt_cv(cv_document: Dict[str, Any]) -> ProfilCandidat:
    """Transforme un `CVParsedFinal` (dict) en `ProfilCandidat` normalisé."""
    cv_document = cv_document or {}
    candidat = cv_document.get("candidat", {}) or {}
    reco = cv_document.get("recommandations_agentiques", {}) or {}

    experiences = candidat.get("experiences", []) or []
    projets_raw = candidat.get("projets", []) or []
    skills = candidat.get("skills", {}) or {}
    hard_skills_raw = skills.get("hard_skills", []) or []
    soft_skills_raw = skills.get("soft_skills", []) or []

    tech_projets = _collect_project_techs(projets_raw)
    tech_exp = _collect_tech_experience_terms(experiences)

    hard_skills: List[SkillEval] = []
    for hs in hard_skills_raw:
        nom = hs.get("skill", "")
        contexte = hs.get("context", "")
        niveau = _derive_niveau_maitrise(nom, contexte, tech_projets, tech_exp)
        hard_skills.append(
            SkillEval(
                nom=nom,
                contexte=contexte,
                niveau_maitrise=niveau,
                # À valider si non éprouvée en projet/prod.
                a_valider_entretien=niveau in ("declare", "academique"),
            )
        )

    soft_skills = [
        SoftSkillEval(nom=ss.get("skill", ""), contexte=ss.get("context", ""))
        for ss in soft_skills_raw
    ]

    projets = [
        ProjetResume(
            title=p.get("title", ""),
            technologies=p.get("technologies", []) or [],
            score_pourcent=p.get("score_general_projet_pourcent"),
            avis_cto=p.get("avis_cto"),
        )
        for p in projets_raw
    ]

    profils_kg = reco.get("profil_calcule_knowledge_graph", []) or []
    metier_cible = profils_kg[0].get("nom") if profils_kg else None
    metier_conf = float(profils_kg[0].get("confidence", 0.0)) if profils_kg else 0.0

    return ProfilCandidat(
        first_name=candidat.get("first_name") or "Candidat",
        poste_vise=candidat.get("poste_vise_header"),
        introduction=candidat.get("introduction"),
        is_reconversion=bool(candidat.get("is_reconversion")),
        is_etudiant=bool(candidat.get("is_etudiant")),
        is_disponible=candidat.get("is_disponible"),
        hard_skills=hard_skills,
        soft_skills=soft_skills,
        competences_transferables=_build_transferables(soft_skills_raw, experiences),
        projets=projets,
        metier_cible=metier_cible,
        metier_confidence=metier_conf,
        axes_entretien=_build_axes(reco, candidat.get("entretien_guide")),
    )
