"""Test end-to-end de la finalisation (étape 6) — évaluateur LLM mocké.

Vérifie que le rapport final est cohérent et complet pour un profil atypique
(reconvertie, D1 modeste mais D3/D4 forts) : compensation, argument démo,
positionnement inclusif, feedback non vide, radar, intégrité.
"""

import src.report.pipeline as pipeline
from src.context.interview_context import build_interview_context
from src.graph.state import segment_qa
from src.schemas.signals_schema import SignalUnit
from tests.fixtures import CV_RECONVERSION_DATA, OFFRE_DATA_ANALYST


def _full_transcript():
    msgs = []
    contenus_user = [
        "Je me suis reconvertie après 6 ans en pâtisserie, je me suis formée seule "
        "en SQL puis en bootcamp, en montant des projets de plus en plus durs.",
        "J'ai appris de mes erreurs : mon premier dashboard était faux, j'ai compris "
        "pourquoi et refait toute la modélisation.",
        "En un an je suis passée de zéro à un pipeline complet, ma méthode c'est de "
        "construire un projet réel à chaque concept.",
        "J'ai choisi Postgres pour les jointures complexes, mais je connais ses limites "
        "sur le volume.",
        "Une fois ma requête plantait à cause d'un index manquant, j'ai diagnostiqué "
        "avec EXPLAIN.",
        "Je documentais mes requêtes pour l'équipe.",
        "Quand je gérais ma pâtisserie, je suivais mes marges chaque semaine sur Excel, "
        "j'ai réduit mes pertes de 15%.",
        "Je faisais le lien entre les chiffres et les décisions concrètes d'achat.",
        "Face au dashboard incohérent, je vérifierais d'abord le périmètre de calcul.",
        "Si c'est TTC vs HT, je clarifierais avec le métier avant de corriger.",
        "Ma prochaine étape c'est dbt pour structurer mes transformations.",
    ]
    for i, u in enumerate(contenus_user):
        msgs.append({"role": "assistant", "content": f"question {i}"})
        msgs.append({"role": "user", "content": u})
    return msgs


def _mock_signals(messages):
    """Signaux crafted : D1 modeste, D3 fort, D4 confirmé, D2 correct."""
    items = segment_qa(messages)
    units = []
    for it in items:
        if it.section == "icebreaker":
            units.append(SignalUnit(
                dimension="D3_trajectoire", question_id=it.question_id,
                indicators={"auto_formation_documentee": True, "apprend_de_echecs": True,
                            "projets_difficulte_croissante": True, "methode_explicite": True,
                            "delta_12_mois": True, "prochaine_marche_claire": True},
                verbatim=it.answer[:80]))
            units.append(SignalUnit(dimension="D5_communication", question_id=it.question_id,
                                    indicators={"comprehensible": True, "reponse_structuree": True},
                                    verbatim=it.answer[:40]))
        elif it.section == "auditeur":
            units.append(SignalUnit(
                dimension="D1_profondeur_technique", question_id=it.question_id,
                indicators={"decrit_usage": True, "justifie_choix": True},
                verbatim=it.answer[:80]))
            units.append(SignalUnit(dimension="D6_fiabilite", question_id=it.question_id,
                                    indicators={"coherence_reponses": True, "constance_cv_entretien": True,
                                                "honnetete_intellectuelle": True}, verbatim=it.answer[:40]))
        elif it.section == "enqueteur":
            units.append(SignalUnit(
                dimension="D4_transferable", question_id=it.question_id,
                indicators={"competence_identifiee": True, "situation_concrete": True,
                            "applicabilite_tech_demontree": True, "exemple_chiffre": True},
                verbatim=it.answer[:80]))
        elif it.section == "stratege":
            units.append(SignalUnit(
                dimension="D2_raisonnement", question_id=it.question_id,
                indicators={"comprend_probleme": True, "demarche_structuree": True,
                            "pertinence_technique": True}, verbatim=it.answer[:80]))
        elif it.section == "projecteur":
            units.append(SignalUnit(
                dimension="D3_trajectoire", question_id=it.question_id,
                indicators={"prochaine_marche_claire": True, "auto_formation_documentee": True},
                verbatim=it.answer[:80]))
    return units


def test_full_pipeline_profil_atypique():
    pipeline.evaluate_transcript = _mock_signals  # mock du juge LLM
    ctx = build_interview_context(CV_RECONVERSION_DATA, OFFRE_DATA_ANALYST)
    report = pipeline.build_final_result(ctx, _full_transcript())

    # Dimensions présentes (6).
    dims = {d["dimension"]: d for d in report["dimensions"]}
    assert len(dims) == 6
    assert dims["D3_trajectoire"]["score"] >= 4         # apprend vite
    assert dims["D1_profondeur_technique"]["score"] <= 3  # socle modeste

    # Adéquation inclusive : il y a des couverts et/ou des compensations.
    adq = report["adequation"]
    assert adq["couvert"] or adq["compense_par"]

    # Positionnement inclusif (prêt pour un poste, au moins junior).
    assert report["positionnement"]["pret_pour"]

    # Argument démo présent (D3 fort + compensations).
    assert isinstance(report["argument_demo"], str)

    # Feedback candidat non vide, radar D1-D5 présent.
    assert report["feedback_candidat"]
    assert len(report["radar_candidat"]) == 5

    # Intégrité calculée (non bloquante).
    assert "suspicion_score" in report["integrite"]

    # Preuves auditables présentes sur D3.
    assert any(p["type"] == "verbatim" for p in dims["D3_trajectoire"]["preuves"])


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
