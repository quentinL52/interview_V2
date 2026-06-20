"""Tests des parties déterministes de l'évaluateur (étape 4) — sans LLM.

Segmentation du transcript, conversion sortie juge -> SignalUnit (avec filtrage
des indicateurs hors-liste), et fallback neutre quand le LLM est indisponible.
"""

from src.graph.evaluator import (
    DimensionSignal,
    PhaseExtraction,
    QuestionEval,
    _neutral_signals,
    _to_signal_units,
)
from src.graph.state import SECTION_ORDER, TOTAL_QUESTIONS, segment_qa


def _full_transcript():
    msgs = []
    for i in range(TOTAL_QUESTIONS):
        msgs.append({"role": "assistant", "content": f"question {i}"})
        msgs.append({"role": "user", "content": f"réponse {i}"})
    return msgs


def test_segment_qa_couvre_toutes_les_phases():
    items = segment_qa(_full_transcript())
    assert len(items) == TOTAL_QUESTIONS
    sections = {it.section for it in items}
    assert sections == set(SECTION_ORDER)
    # Chaque item porte ses dimensions (primaire + transverses).
    auditeur = next(it for it in items if it.section == "auditeur")
    assert "D1_profondeur_technique" in auditeur.dimensions
    assert "D5_communication" in auditeur.dimensions


def test_segment_qa_reponse_manquante():
    # Question posée mais pas encore de réponse : answer vide, pas de crash.
    items = segment_qa([{"role": "assistant", "content": "q0"}])
    assert len(items) == 1
    assert items[0].answer == ""


def test_to_signal_units_filtre_indicateurs_hors_liste():
    items = segment_qa(_full_transcript())
    auditeur = next(it for it in items if it.section == "auditeur")
    extraction = PhaseExtraction(evaluations=[
        QuestionEval(question_id=auditeur.question_id, signals=[
            DimensionSignal(
                dimension="D1_profondeur_technique",
                # 'justifie_choix' est valide ; 'invente_indicateur' doit être filtré.
                indicateurs_presents=["justifie_choix", "invente_indicateur"],
                verbatim="J'ai choisi Postgres pour les jointures.",
            )
        ])
    ])
    units = _to_signal_units(extraction, items)
    assert len(units) == 1
    assert units[0].indicators == {"justifie_choix": True}
    assert units[0].verbatim.startswith("J'ai choisi")


def test_to_signal_units_ignore_dimension_inconnue():
    items = segment_qa(_full_transcript())
    qid = items[0].question_id
    extraction = PhaseExtraction(evaluations=[
        QuestionEval(question_id=qid, signals=[
            DimensionSignal(dimension="D99_inexistante", indicateurs_presents=["x"])
        ])
    ])
    assert _to_signal_units(extraction, items) == []


def test_neutral_signals():
    items = segment_qa(_full_transcript())[:2]
    units = _neutral_signals(["D1_profondeur_technique", "D5_communication"], items)
    assert len(units) == 4  # 2 questions x 2 dimensions
    assert all(u.indicators == {} for u in units)


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
