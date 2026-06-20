"""Tests du routage conversationnel + garantie anti-boucle (étape 3) — sans LLM.

On mocke la génération LLM pour valider uniquement la logique de progression :
ordre des phases, budget de questions, et surtout l'impossibilité de boucler.
"""

import src.graph.agents as agents_mod
import src.graph.orchestrator as orch_mod
from src.graph.state import TOTAL_QUESTIONS, SECTION_ORDER, compute_progress
from tests.fixtures import CV_RECONVERSION_DATA, OFFRE_DATA_ANALYST


def _fake_generate(ctx, section, history, index_in_section):
    return f"[{section}#{index_in_section}] question ?"


def _fake_report(ctx, convo):
    return {"ok": True, "n_messages": len(convo)}


def _processor(monkeypatch=None):
    agents_mod_ref = orch_mod.generate_question  # not used; patch module attr below
    return orch_mod.InterviewProcessor(
        {"cv_document": CV_RECONVERSION_DATA, "job_offer": OFFRE_DATA_ANALYST}
    )


def test_section_order_progression():
    # On simule un entretien complet en suivant l'ordre attendu des phases.
    orch_mod.generate_question = _fake_generate
    proc = _processor()

    messages = []
    seen_sections = []
    # Joue jusqu'à finalisation (avec une marge de sécurité).
    for _ in range(TOTAL_QUESTIONS + 2):
        result = proc.step(messages)
        if result["status"] == "finished":
            break
        seen_sections.append(result["current_agent"])
        # L'assistant pose la question, le candidat répond.
        messages.append({"role": "assistant", "content": result["response"]})
        messages.append({"role": "user", "content": "Voici ma réponse."})

    # Les 5 phases ont été traversées dans l'ordre.
    ordered_unique = []
    for s in seen_sections:
        if not ordered_unique or ordered_unique[-1] != s:
            ordered_unique.append(s)
    assert ordered_unique == SECTION_ORDER
    assert len(seen_sections) == TOTAL_QUESTIONS


def test_finalize_after_budget():
    orch_mod.generate_question = _fake_generate
    monkey = orch_mod
    proc = _processor()

    # Construit un historique complet (toutes questions répondues).
    messages = []
    for i in range(TOTAL_QUESTIONS):
        messages.append({"role": "assistant", "content": f"q{i}"})
        messages.append({"role": "user", "content": f"r{i}"})

    # Mocke la génération du rapport pour éviter la chaîne LLM.
    import sys
    import types

    fake_pipeline = types.ModuleType("src.report.pipeline")
    fake_pipeline.build_final_result = _fake_report
    sys.modules["src.report.pipeline"] = fake_pipeline

    result = proc.step(messages)
    assert result["status"] == "finished"
    assert result["current_agent"] == "final"
    assert result["report"]["ok"] is True


def test_anti_boucle_jamais_de_repetition_de_phase_au_dela_budget():
    # Même si on continue à empiler des messages, on ne reste jamais bloqué :
    # au-delà du budget, should_finalize est vrai.
    convo = []
    for i in range(TOTAL_QUESTIONS + 5):
        convo.append({"role": "assistant", "content": f"q{i}"})
        convo.append({"role": "user", "content": f"r{i}"})
    progress = compute_progress(convo)
    assert progress.should_finalize is True


def test_premier_tour_icebreaker():
    progress = compute_progress([])
    assert progress.is_first_turn is True
    assert progress.section == "icebreaker"
    assert progress.index_in_section == 0


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
