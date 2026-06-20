"""Agents intervieweurs : génèrent la prochaine question (chaleureux, contextualisé).

Un seul persona (Roni) décliné par phase. Chaque phase reçoit le bon contexte
métier + offre, sans jamais que le candidat sente un changement d'agent.

Le LLM ne fait QUE converser ici : aucune évaluation, aucun score.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from src.core.config import interviewer_llm
from src.referentiel.fiches_metier import critical_skills, get_sjt_scenario
from src.schemas.context_schema import InterviewContext

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_BASE_TEMPLATE = (_PROMPT_DIR / "interviewer_base.txt").read_text(encoding="utf-8")

# Missions par phase (injectées dans le template de base).
_SECTION_MISSIONS = {
    "icebreaker": (
        "Mettre le candidat en confiance, comprendre son parcours et ses "
        "motivations réelles, et amorcer la compréhension de SA façon d'apprendre. "
        "Si reconversion : explore avec respect ce qui l'a décidé à changer. "
        "Si étudiant : comprends la cohérence entre sa formation et le poste."
    ),
    "auditeur": (
        "Comprendre la PROFONDEUR TECHNIQUE RÉELLE du candidat (pas déclarée). "
        "Choisis une compétence critique du poste ou un projet concret, et fais-le "
        "expliquer ses CHOIX, les limites qu'il connaît, un vrai problème qu'il a "
        "résolu. Cherche le concret, pas la récitation."
    ),
    "enqueteur": (
        "Explorer ce que le CV ne dit pas : le capital transférable et la posture. "
        "Fais raconter une SITUATION CONCRÈTE où une compétence (même acquise hors "
        "tech) s'est exprimée, et fais le pont avec le poste. Cherche le vécu, pas "
        "les grands mots."
    ),
    "stratege": (
        "Tester le RAISONNEMENT face à un problème inconnu via une mise en "
        "situation réaliste du métier. Présente le scénario ci-dessous, laisse le "
        "candidat dérouler sa démarche. Tu n'attends pas une bonne réponse, tu "
        "observes COMMENT il pense."
    ),
    "projecteur": (
        "Comprendre sa trajectoire d'apprentissage et sa projection : quelle est sa "
        "méthode pour progresser, et quelle est la prochaine compétence qu'il vise "
        "pour réussir à CE poste, à court terme."
    ),
}


def _profil_flags(ctx: InterviewContext) -> str:
    flags = []
    p = ctx.profil
    if p.is_reconversion:
        flags.append("en reconversion")
    if p.is_etudiant:
        flags.append("étudiant")
    if p.is_disponible:
        flags.append("disponible")
    return ", ".join(flags) if flags else "parcours standard"


def _offer_block(ctx: InterviewContext) -> str:
    a = ctx.attendus
    if not a.is_fournie:
        return "Pas d'offre précise — appuie-toi sur le métier cible générique."
    lines = []
    if a.entreprise:
        lines.append(f"- Entreprise : {a.entreprise}")
    if a.mission:
        lines.append(f"- Mission : {a.mission}")
    if a.profil_recherche:
        lines.append(f"- Profil recherché : {a.profil_recherche}")
    if a.competences_attendues:
        lines.append(f"- Compétences attendues : {', '.join(a.competences_attendues)}")
    lines.append(f"- Séniorité visée : {a.seniorite}")
    return "\n".join(lines)


def _axes_for(ctx: InterviewContext, agent: str, limit: int = 3) -> List[str]:
    axes = [a for a in ctx.profil.axes_entretien if a.agent == agent]
    # Priorité : urgence haute d'abord.
    order = {"haute": 0, "moyenne": 1, "faible": 2}
    axes.sort(key=lambda a: order.get(a.niveau_urgence, 1))
    return [
        f"[{a.niveau_urgence}] {a.theme} — piste : {a.question_guide}".strip(" —")
        for a in axes[:limit]
    ]


def _context_block(ctx: InterviewContext, section: str) -> str:
    p = ctx.profil
    lines: List[str] = []

    if section == "icebreaker":
        if p.introduction:
            lines.append(f"Intro du CV : {p.introduction}")
        lines += _axes_for(ctx, "icebreaker")
        if not lines:
            lines.append("Comprends son parcours et ce qui l'amène vers ce métier.")

    elif section == "auditeur":
        a_valider = [s.nom for s in p.hard_skills if s.a_valider_entretien][:6]
        critiques = [s.nom for s in p.hard_skills if s.critique_offre][:6]
        if critiques:
            lines.append(f"Compétences attendues par l'offre à sonder : {', '.join(critiques)}")
        if a_valider:
            lines.append(f"Compétences peu éprouvées (à valider) : {', '.join(a_valider)}")
        if ctx.skills_critiques:
            lines.append(f"Compétences critiques du poste non prouvées sur le CV : {', '.join(ctx.skills_critiques[:5])}")
        if p.projets:
            proj = p.projets[0]
            lines.append(f"Projet à creuser : '{proj.title}' ({', '.join(proj.technologies)})")
        lines += _axes_for(ctx, "auditeur")

    elif section == "enqueteur":
        for t in p.competences_transferables[:3]:
            lines.append(f"Transférable à confirmer : {t.competence} (source : {t.source})")
        soft = [s.nom for s in p.soft_skills][:4]
        if soft:
            lines.append(f"Soft skills déclarés : {', '.join(soft)}")
        lines += _axes_for(ctx, "enqueteur")

    elif section == "stratege":
        scenario = get_sjt_scenario(p.metier_cible, ctx.attendus, ctx.fiche_metier)
        lines.append(f"SCÉNARIO à présenter : {scenario.contexte}")
        lines.append(f"CONTRAINTE à ajouter au 2e échange si tu y reviens : {scenario.contrainte_ajoutee}")

    elif section == "projecteur":
        if ctx.skills_critiques:
            lines.append(f"Prochaines compétences utiles au poste : {', '.join(ctx.skills_critiques[:4])}")
        lines.append(f"Métier cible : {p.metier_cible or ctx.attendus.poste or 'data/IA'}")
        lines += _axes_for(ctx, "projecteur")

    return "\n".join(f"- {l}" if not l.startswith(("-", "[", "SCÉNARIO", "CONTRAINTE", "Intro")) else l for l in lines) or "- Explore librement et avec curiosité."


def build_system_prompt(ctx: InterviewContext, section: str) -> str:
    p = ctx.profil
    return _BASE_TEMPLATE.format(
        first_name=p.first_name,
        poste_vise=p.poste_vise or ctx.attendus.poste or "non précisé",
        metier_cible=p.metier_cible or "à confirmer",
        profil_flags=_profil_flags(ctx),
        offer_block=_offer_block(ctx),
        section_mission=_SECTION_MISSIONS.get(section, ""),
        context_block=_context_block(ctx, section),
    )


def generate_question(
    ctx: InterviewContext,
    section: str,
    history: List[Dict[str, str]],
    index_in_section: int,
) -> str:
    """Génère la prochaine intervention de Roni pour la phase donnée."""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    system = build_system_prompt(ctx, section)
    if section == "icebreaker" and index_in_section == 0:
        system += (
            "\n\nC'est le TOUT DÉBUT de l'entretien : salue chaleureusement "
            f"{ctx.profil.first_name}, présente-toi en une phrase (Roni, pour un "
            "entretien d'entraînement), puis pose ta première question."
        )

    llm_messages = [SystemMessage(content=system)]
    for m in history:
        role = m.get("role")
        content = m.get("content", "")
        if role == "user":
            llm_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            llm_messages.append(AIMessage(content=content))

    response = interviewer_llm().invoke(llm_messages)
    return response.content.strip()
