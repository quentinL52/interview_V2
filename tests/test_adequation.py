"""Tests adéquation poste + positionnement (étape 5) — déterministe, sans LLM.

Vérifie le cœur AIRH : un manque technique est COMPENSÉ (jamais éliminatoire)
par une forte trajectoire d'apprentissage, et le positionnement reste inclusif.
"""

from src.context.interview_context import build_interview_context
from src.referentiel.fiches_metier import famille_metier, get_sjt_scenario
from src.scoring.adequation_poste import evaluer_adequation
from src.scoring.positionnement import positionner
from src.schemas.signals_schema import DimensionScore
from tests.fixtures import CV_RECONVERSION_DATA, OFFRE_DATA_ANALYST


def _scores(d1, d2, d3, d4=2, d5=3, d6=3):
    return [
        DimensionScore(dimension="D1_profondeur_technique", score=d1, confiance="haute"),
        DimensionScore(dimension="D2_raisonnement", score=d2, confiance="moyenne"),
        DimensionScore(dimension="D3_trajectoire", score=d3, confiance="haute"),
        DimensionScore(dimension="D4_transferable", score=d4, confiance="moyenne"),
        DimensionScore(dimension="D5_communication", score=d5, confiance="moyenne"),
        DimensionScore(dimension="D6_fiabilite", score=d6, confiance="moyenne"),
    ]


def test_adequation_couvre_skills_prouves():
    ctx = build_interview_context(CV_RECONVERSION_DATA, OFFRE_DATA_ANALYST)
    adq = evaluer_adequation(ctx, _scores(3, 3, 4))
    couverts = " ".join(i.competence for i in adq.couvert).lower()
    # SQL et Power BI sont prouvés en projet -> couverts.
    assert "sql" in couverts or "power bi" in couverts
    # Chaque item couvert est justifié.
    assert all(i.justification for i in adq.couvert)


def test_manque_compense_par_apprentissage():
    ctx = build_interview_context(CV_RECONVERSION_DATA, OFFRE_DATA_ANALYST)
    # D1 faible mais D3 forte : les manques doivent être COMPENSÉS, pas éliminés.
    adq = evaluer_adequation(ctx, _scores(d1=1, d2=4, d3=5))
    assert len(adq.compense_par) >= 1
    assert all("compensable" in i.justification.lower() for i in adq.compense_par)


def test_positionnement_inclusif_reconverti_apprend_vite():
    ctx = build_interview_context(CV_RECONVERSION_DATA, OFFRE_DATA_ANALYST)
    scores = _scores(d1=2, d2=4, d3=5)
    adq = evaluer_adequation(ctx, scores)
    pos = positionner(ctx, scores, adq)
    # Inclusif : prêt pour un poste junior malgré D1 modeste.
    assert any("junior" in r.lower() for r in pos.pret_pour)
    # La condition de réussite mentionne l'accompagnement (apprend vite).
    assert "référent" in pos.conditions_de_reussite or "senior" in pos.conditions_de_reussite
    assert pos.profil_resume


def test_positionnement_socle_solide():
    ctx = build_interview_context(CV_RECONVERSION_DATA, OFFRE_DATA_ANALYST)
    scores = _scores(d1=4, d2=4, d3=3)
    adq = evaluer_adequation(ctx, scores)
    pos = positionner(ctx, scores, adq)
    assert pos.pret_pour


def test_scenario_sjt_par_famille():
    ctx = build_interview_context(CV_RECONVERSION_DATA, OFFRE_DATA_ANALYST)
    # Data Analyst -> famille analyst.
    assert famille_metier(ctx.profil.metier_cible, ctx.attendus, ctx.fiche_metier) == "analyst"
    scenario = get_sjt_scenario(ctx.profil.metier_cible, ctx.attendus, ctx.fiche_metier)
    assert scenario.famille == "analyst"
    assert scenario.contrainte_ajoutee


if __name__ == "__main__":
    import sys
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} tests passés.")
    sys.exit(1 if failed else 0)
