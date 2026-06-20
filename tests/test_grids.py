"""Tests des grilles déterministes D1-D6 (étape 2) — aucun LLM.

Vérifie : fidélité aux ancres (chaque niveau), règles dures (défaut 0,
réponse générique/hors-sujet non créditées, niveau 5 verrouillé), arrondi
conservateur, et calcul de confiance.
"""

from src.scoring.grids import (
    certitude_from_d4,
    gate_d1,
    gate_d2,
    gate_d3,
    gate_d4,
    gate_d5,
    gate_d6,
    score_signal,
)
from src.scoring.dimensions import aggregate_dimension, _conservative_round
from src.schemas.signals_schema import SignalUnit


# --- D1 : profondeur technique ------------------------------------------- #

def test_d1_defaut_zero():
    assert gate_d1({}) == 0


def test_d1_paliers():
    assert gate_d1({"decrit_usage": True}) == 1
    assert gate_d1({"decrit_usage": True, "justifie_choix": True}) == 2
    assert gate_d1({"justifie_choix": True, "identifie_limites": True, "raconte_debug_reel": True}) == 3
    assert gate_d1({
        "justifie_choix": True, "identifie_limites": True, "raconte_debug_reel": True,
        "propose_alternatives": True,
    }) == 4
    assert gate_d1({
        "justifie_choix": True, "identifie_limites": True, "raconte_debug_reel": True,
        "propose_alternatives": True, "decisions_archi_production": True,
    }) == 5


def test_d1_niveau5_verrouille_sans_palier_4():
    # Décisions archi seules, sans le socle, ne donnent PAS 5.
    assert gate_d1({"decisions_archi_production": True, "fait_monter_autres": True}) == 0


def test_d1_reponse_generique_non_creditee():
    full = {
        "justifie_choix": True, "identifie_limites": True, "raconte_debug_reel": True,
        "propose_alternatives": True,
    }
    assert gate_d1(full, reponse_generique=True) == 0
    assert gate_d1(full, hors_sujet=True) == 0


# --- D2 : raisonnement ---------------------------------------------------- #

def test_d2_paliers():
    assert gate_d2({"comprend_probleme": True}) == 1
    assert gate_d2({"demarche_structuree": True}) == 2
    assert gate_d2({"demarche_structuree": True, "pertinence_technique": True}) == 3
    assert gate_d2({
        "demarche_structuree": True, "pertinence_technique": True, "gere_contrainte_ajoutee": True,
    }) == 4
    assert gate_d2({
        "demarche_structuree": True, "pertinence_technique": True, "gere_contrainte_ajoutee": True,
        "admet_inconnu_avec_methode": True,
    }) == 5


# --- D3 : trajectoire (atypiques) ---------------------------------------- #

def test_d3_reconverti_apprend_vite():
    # Un profil qui s'auto-forme, monte en difficulté, a une méthode et un delta.
    score = gate_d3({
        "auto_formation_documentee": True, "apprend_de_echecs": True,
        "projets_difficulte_croissante": True, "methode_explicite": True,
        "delta_12_mois": True, "prochaine_marche_claire": True,
    })
    assert score == 5


def test_d3_vague():
    assert gate_d3({"auto_formation_documentee": True}) == 2
    assert gate_d3({}) == 0


# --- D4 : transférable ---------------------------------------------------- #

def test_d4_pont_confirme():
    score = gate_d4({
        "competence_identifiee": True, "situation_concrete": True,
        "applicabilite_tech_demontree": True, "exemple_chiffre": True,
    })
    assert score == 5
    assert certitude_from_d4(score) == "confirme"


def test_d4_probable_puis_flou():
    s3 = gate_d4({"situation_concrete": True, "applicabilite_tech_demontree": True})
    assert s3 == 3
    assert certitude_from_d4(s3) == "probable"
    assert certitude_from_d4(0) == "flou"


# --- D5 : communication --------------------------------------------------- #

def test_d5_clair_vs_confus():
    assert gate_d5({"comprehensible": True, "reponse_structuree": True}) == 3
    assert gate_d5({"reponse_structuree": True}) == 1
    assert gate_d5({}, hors_sujet=True) == 0


# --- D6 : fiabilité (signaux négatifs plafonnent) ------------------------ #

def test_d6_honnete_coherent():
    assert gate_d6({
        "coherence_reponses": True, "constance_cv_entretien": True,
        "honnetete_intellectuelle": True, "lucidite_sur_soi": True,
    }) == 5


def test_d6_bluff_plafonne():
    # Même avec des signaux positifs, un bluff détecté plafonne bas.
    assert gate_d6({"bluff_detecte": True, "honnetete_intellectuelle": True}) == 1
    assert gate_d6({"bluff_detecte": True, "ecart_cv_entretien": True}) == 0


# --- Arrondi conservateur ------------------------------------------------- #

def test_conservative_round():
    assert _conservative_round(2.5) == 2       # le doute ne profite pas au score
    assert _conservative_round(2.6) == 3
    assert _conservative_round(3.0) == 3


# --- Agrégation + confiance ---------------------------------------------- #

def test_aggregate_confiance_haute():
    units = [
        SignalUnit(dimension="D1_profondeur_technique", question_id="auditeur_q1",
                   indicators={"decrit_usage": True, "justifie_choix": True}, verbatim="J'ai choisi X parce que..."),
        SignalUnit(dimension="D1_profondeur_technique", question_id="auditeur_q2",
                   indicators={"justifie_choix": True, "identifie_limites": True, "raconte_debug_reel": True},
                   verbatim="Une fois la requête plantait car..."),
        SignalUnit(dimension="D1_profondeur_technique", question_id="auditeur_q3",
                   indicators={"justifie_choix": True}, verbatim="On utilisait Postgres pour..."),
    ]
    res = aggregate_dimension("D1_profondeur_technique", units)
    assert res.score >= 2
    assert res.confiance == "haute"
    assert any(p.type == "verbatim" for p in res.preuves)


def test_aggregate_confiance_faible_si_evasif():
    units = [
        SignalUnit(dimension="D1_profondeur_technique", question_id="q1",
                   indicators={}, reponse_generique=True),
    ]
    res = aggregate_dimension("D1_profondeur_technique", units)
    assert res.score == 0
    assert res.confiance == "faible"


def test_score_signal_registry():
    # L'API par nom de dimension fonctionne pour les 6 grilles.
    for dim in ["D1_profondeur_technique", "D2_raisonnement", "D3_trajectoire",
                "D4_transferable", "D5_communication", "D6_fiabilite"]:
        assert score_signal(dim, {}) == 0


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
