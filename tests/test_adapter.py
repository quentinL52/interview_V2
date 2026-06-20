"""Tests de la couche d'adaptation (étape 1) — sans LLM.

Vérifie que la sortie réelle du parser v1.5 + une offre produisent un
`InterviewContext` cohérent, et que les dérivations clés du cœur AIRH
fonctionnent (niveau de maîtrise, capital transférable, skills critiques de
l'offre, routage des axes d'entretien).
"""

from src.adapter.cv_adapter import adapt_cv
from src.adapter.offer_adapter import adapt_offer
from src.context.interview_context import build_interview_context
from tests.fixtures import CV_RECONVERSION_DATA, OFFRE_DATA_ANALYST


def _skill(profil, nom):
    return next(s for s in profil.hard_skills if s.nom == nom)


def test_cv_adapter_niveau_maitrise():
    profil = adapt_cv(CV_RECONVERSION_DATA)
    # SQL et Python sont dans le projet -> au moins niveau projet.
    assert _skill(profil, "SQL").niveau_maitrise in ("projet", "production")
    assert _skill(profil, "Python").niveau_maitrise in ("projet", "production")
    # Java vu uniquement en cours -> académique, à valider.
    java = _skill(profil, "Java")
    assert java.niveau_maitrise == "academique"
    assert java.a_valider_entretien is True


def test_cv_adapter_transferables():
    profil = adapt_cv(CV_RECONVERSION_DATA)
    competences = [t.competence for t in profil.competences_transferables]
    # La gestion d'entreprise (transferable=Élevée) doit remonter en 'probable'.
    gestion = next(t for t in profil.competences_transferables if "Gestion" in t.competence)
    assert gestion.certitude == "probable"
    # L'expérience non-tech bien notée par Roni génère un capital transférable.
    assert any("pâtisserie" in t.source.lower() or "Gérante" in t.source for t in profil.competences_transferables)
    assert len(competences) >= 2


def test_cv_adapter_metier_cible_et_axes():
    profil = adapt_cv(CV_RECONVERSION_DATA)
    assert profil.metier_cible == "Data Analyst"
    assert profil.metier_confidence > 0.5
    # Les 3 axes sont routés vers des agents distincts pertinents.
    agents = {a.agent for a in profil.axes_entretien}
    assert "icebreaker" in agents          # transition/motivation
    assert "auditeur" in agents            # profondeur SQL
    assert any(a.agent == "enqueteur" for a in profil.axes_entretien)  # gestion transférable


def test_offer_adapter():
    attendus = adapt_offer(OFFRE_DATA_ANALYST)
    assert attendus.is_fournie is True
    assert attendus.seniorite == "junior"          # "Junior" + "Première expérience"
    assert "SQL" in attendus.competences_attendues
    assert "Power BI" in attendus.competences_attendues
    assert len(attendus.competences_attendues) >= 4


def test_interview_context_skills_critiques_et_offre():
    ctx = build_interview_context(CV_RECONVERSION_DATA, OFFRE_DATA_ANALYST)
    # SQL et Power BI sont attendus par l'offre -> marqués critique_offre.
    sql = _skill(ctx.profil, "SQL")
    assert sql.critique_offre is True
    # Fiche métier résolue depuis le KG (Data Analyst).
    assert ctx.fiche_metier is not None
    assert ctx.fiche_metier.nom == "Data Analyst"
    # Power BI est prouvé seulement en formation (académique) ou projet :
    # le contexte expose des skills critiques à creuser, sans éliminer.
    assert isinstance(ctx.skills_critiques, list)


def test_offer_absente_fallback():
    ctx = build_interview_context(CV_RECONVERSION_DATA, None)
    assert ctx.attendus.is_fournie is False
    # Sans offre, on s'appuie sur la fiche métier générique.
    assert ctx.fiche_metier is not None


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
