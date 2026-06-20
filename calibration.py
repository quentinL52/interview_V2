"""Calibration & contrôle anti-biais du simulateur (étape 7).

Rejoue un batch d'entretiens complets (transcripts réels) à travers la chaîne
d'évaluation réelle (juge LLM + grilles), puis :
- affiche la distribution des scores par dimension et la MOYENNE GLOBALE ;
- ALERTE si la moyenne dépasse 3,5 (grille trop laxiste -> recalibrer) ;
- compare les groupes (ex. `reconverti` vs `classique`) à profil de réponses
  comparable : un écart systématique signale un biais à corriger.

Usage :
    python calibration.py <dossier_cas>

Chaque cas est un fichier JSON :
    { "group": "reconverti", "cv_document": {...}, "job_offer": {...},
      "messages": [{"role": "...", "content": "..."}, ...] }

Nécessite une clé OPENAI_API_KEY valide (appelle le juge réel).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean
from typing import Dict, List

from src.context.interview_context import build_interview_context
from src.core.constants import DIMENSIONS, SEUIL_MOYENNE_ALERTE
from src.report.pipeline import build_final_result


def _load_cases(folder: str) -> List[dict]:
    cases = []
    for path in sorted(Path(folder).glob("*.json")):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
            data["_name"] = path.stem
            cases.append(data)
    return cases


def _run_case(case: dict) -> Dict[str, int]:
    ctx = build_interview_context(case.get("cv_document", {}), case.get("job_offer"))
    report = build_final_result(ctx, case.get("messages", []))
    return {d["dimension"]: d["score"] for d in report["dimensions"]}


def main(folder: str) -> int:
    cases = _load_cases(folder)
    if not cases:
        print(f"Aucun cas .json dans {folder}")
        return 1

    all_scores: List[Dict[str, int]] = []
    by_group: Dict[str, List[float]] = {}

    print(f"\n=== Calibration sur {len(cases)} entretien(s) ===\n")
    for case in cases:
        scores = _run_case(case)
        all_scores.append(scores)
        noted = [v for v in scores.values() if v > 0]
        moy = mean(noted) if noted else 0.0
        group = case.get("group", "n/a")
        by_group.setdefault(group, []).append(moy)
        print(f"- {case['_name']:<24} [{group:<12}] "
              + " ".join(f"{d.split('_')[0]}={scores.get(d, 0)}" for d in DIMENSIONS)
              + f"  (moy={moy:.2f})")

    # Moyenne globale par dimension.
    print("\n--- Moyenne par dimension ---")
    global_means = []
    for d in DIMENSIONS:
        vals = [s.get(d, 0) for s in all_scores]
        m = mean(vals) if vals else 0.0
        global_means.append(m)
        print(f"  {d:<28} {m:.2f}")

    moyenne_globale = mean(global_means)
    print(f"\nMOYENNE GLOBALE : {moyenne_globale:.2f}")
    if moyenne_globale > SEUIL_MOYENNE_ALERTE:
        print(f"  ⚠ ALERTE : > {SEUIL_MOYENNE_ALERTE} — grille trop laxiste, recalibrer.")
    else:
        print(f"  ✓ Sous le seuil de {SEUIL_MOYENNE_ALERTE}.")

    # Comparaison anti-biais entre groupes.
    if len(by_group) > 1:
        print("\n--- Contrôle anti-biais (moyenne par groupe) ---")
        for group, moys in by_group.items():
            print(f"  {group:<16} {mean(moys):.2f}  (n={len(moys)})")
        ecart = max(mean(m) for m in by_group.values()) - min(mean(m) for m in by_group.values())
        print(f"  Écart inter-groupes : {ecart:.2f}")
        if ecart > 1.0:
            print("  ⚠ Écart important entre groupes — vérifier qu'il reflète les "
                  "réponses et non un biais de parcours.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python calibration.py <dossier_cas>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
