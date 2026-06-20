"""Non-régression du scoring déterministe (étape 7) — sans LLM.

Verrouille le comportement des grilles : des jeux de signaux « étalons »
(archétypes) doivent toujours produire les mêmes scores de dimension. Toute
modification d'une grille qui ferait dériver ces valeurs casse ce test —
c'est le garde-fou anti-dérive (complaisance ou sévérité).

Ces archétypes servent aussi de référence de calibration : la moyenne d'un
profil junior/reconverti reste centrée sur 2-3, jamais > 3,5.
"""

from statistics import mean

from src.scoring.dimensions import aggregate_all
from src.schemas.signals_schema import SignalUnit


def _u(dim, qid, **inds):
    return SignalUnit(dimension=dim, question_id=qid, indicators=inds, verbatim="preuve.")


# --- Archétype 1 : reconverti junior solide (apprend vite, socle modeste) --- #
RECONVERTI = [
    _u("D1_profondeur_technique", "auditeur_q0", decrit_usage=True, justifie_choix=True),
    _u("D1_profondeur_technique", "auditeur_q1", justifie_choix=True),
    _u("D3_trajectoire", "icebreaker_q0", auto_formation_documentee=True,
       apprend_de_echecs=True, projets_difficulte_croissante=True, methode_explicite=True,
       delta_12_mois=True, prochaine_marche_claire=True),
    _u("D4_transferable", "enqueteur_q0", competence_identifiee=True, situation_concrete=True,
       applicabilite_tech_demontree=True),
    _u("D2_raisonnement", "stratege_q0", comprend_probleme=True, demarche_structuree=True,
       pertinence_technique=True),
]
RECONVERTI_ATTENDU = {
    "D1_profondeur_technique": 2,   # justifie mais sans limites/debug
    "D3_trajectoire": 5,            # trajectoire exceptionnelle
    "D4_transferable": 3,           # pont démontré
    "D2_raisonnement": 3,
}


# --- Archétype 2 : réponses creuses (rien à créditer) ---------------------- #
CREUX = [
    SignalUnit(dimension="D1_profondeur_technique", question_id="auditeur_q0",
               indicators={}, reponse_generique=True),
    SignalUnit(dimension="D2_raisonnement", question_id="stratege_q0",
               indicators={"comprend_probleme": True}, reponse_generique=True),
]
CREUX_ATTENDU = {"D1_profondeur_technique": 0, "D2_raisonnement": 0}


# --- Archétype 3 : senior confirmé technique ------------------------------- #
SENIOR = [
    _u("D1_profondeur_technique", "auditeur_q0", justifie_choix=True, identifie_limites=True,
       raconte_debug_reel=True, propose_alternatives=True, decisions_archi_production=True),
    _u("D1_profondeur_technique", "auditeur_q1", justifie_choix=True, identifie_limites=True,
       raconte_debug_reel=True, propose_alternatives=True, fait_monter_autres=True),
]
SENIOR_ATTENDU = {"D1_profondeur_technique": 5}


def _scores(units):
    return {d.dimension: d.score for d in aggregate_all(units)}


def test_reconverti_snapshot():
    s = _scores(RECONVERTI)
    for dim, attendu in RECONVERTI_ATTENDU.items():
        assert s[dim] == attendu, f"{dim}: {s[dim]} != {attendu}"


def test_creux_snapshot():
    s = _scores(CREUX)
    for dim, attendu in CREUX_ATTENDU.items():
        assert s[dim] == attendu


def test_senior_snapshot():
    s = _scores(SENIOR)
    assert s["D1_profondeur_technique"] == SENIOR_ATTENDU["D1_profondeur_technique"]


def test_calibration_moyenne_junior_sous_seuil():
    # La moyenne des dimensions notées d'un reconverti junior reste <= 3,5
    # (anti-complaisance), même avec une trajectoire à 5.
    s = _scores(RECONVERTI)
    notes = [v for v in s.values() if v > 0]
    assert mean(notes) <= 3.5


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
