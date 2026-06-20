# AIRH — Simulateur d'Entretien v2

Simulateur d'entretien **ultra-spécialisé data/IA**. Il fait entraîner le
candidat, l'évalue sur 6 dimensions via des **grilles déterministes**, et produit
un rapport recruteur auditable + un feedback candidat utile.

## Principe directeur

> **Le LLM observe et formule. Le code décide et note.**

Le LLM ne fait que (1) **mener la conversation** (chaleureuse, adaptative) et
(2) **extraire des indicateurs observables** (booléens + verbatims). Tout le
reste — scores 0-5, confiance, adéquation au poste, positionnement, rapports —
est du **Python déterministe et testable**. C'est ce qui rend le score
*auditable* (AI Act Art. 13/14), *non-complaisant*, et impossible à reproduire
avec un LLM grand public.

## Ce que le module évalue — 6 dimensions

| Dim | Intitulé | Mesurée par |
|---|---|---|
| D1 | Profondeur technique validée | Auditeur |
| D2 | Raisonnement & résolution de problème | Stratège (mise en situation) |
| D3 | Trajectoire d'apprentissage *(cœur atypiques)* | Icebreaker + Projecteur |
| D4 | Capital transférable *(ce que le CV ne dit pas)* | Enquêteur |
| D5 | Communication technique | transverse |
| D6 | Fiabilité professionnelle | transverse + anti-triche |

**D2 + D3 + D4** révèlent les talents atypiques que les filtres ATS écartent.

## Architecture

```
payload (CV parsé v1.5 + offre + messages)
        │
   adapter/  ──► ProfilCandidat + AttendusPoste          (dérive niveau_maitrise,
        │                                                  transférables, axes)
   context/  ──► InterviewContext (+ fiche métier)        (croise skills ↔ offre)
        │
   graph/    ──► orchestrator : 5 phases, anti-boucle, fluidité
        │        agents       : Roni (conversation, 0 évaluation)
        │        evaluator    : juge froid (temp 0) → SignalUnit[]
        │
   scoring/  ──► grids (ancres D1-D6) → dimensions (triplets) 
        │        adequation_poste (inclusive) + positionnement
   integrity/──► anti_cheat (local, 0 token)
   report/   ──► recruiter_report + candidate_feedback → SimulationReportV2
```

### Contrat avec le parser (`module_analyse_cv_v1.5`)

Le simulateur **n'exige aucune modification du parser**. La couche
`adapter/cv_adapter.py` dérive ce que la v1.5 ne produit pas encore
(`niveau_maitrise`, `a_valider_entretien`, capital transférable structuré) à
partir de ce qui existe (`hard_skills[].context`, `projets[].technologies`,
`experiences[].evaluation_roni`, `soft_skills[].transferable`,
`axes_entretien_simulateur`, `profil_calcule_knowledge_graph`). Si un
`entretien_guide` structuré apparaît un jour côté parser, l'adapter le détecte
et l'utilise (compat ascendante).

Le **référentiel métier** réutilise `metiers.json` du parser (résolution
automatique du chemin ; surchargeable via `METIERS_JSON_PATH`).

## Anti-boucle & fluidité

- La progression suit un **budget de questions** (≈11), dérivé du nombre de
  messages — jamais l'attente d'une réponse « parfaite » (le défaut de la v1).
  Un cap dur force la finalisation. → **aucune boucle possible**.
- Transitions imperceptibles : une seule conversation continue (Roni), le
  candidat ne perçoit pas les phases.

## Optimisation des tokens

- Pas de crew CrewAI (−~25k tokens vs v1).
- Évaluation = ~5 appels structurés (1/phase), sans l'historique chaleureux.
- Anti-triche + détection de réponses génériques **100 % locales** (0 token).
- Rapports + adéquation + positionnement **déterministes** (0 token).
- 1 seul appel LLM pour rédiger le feedback candidat (fallback templaté = 0 token).
- Cible : ~30-40k tokens/entretien (vs ~70-80k en v1).

## Lancer

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=...        # Windows: $env:OPENAI_API_KEY="..."
python main.py                   # POST /simulate-interview/  (port 7861)
```

Contrat HTTP identique à la v1 (`{user_id, job_offer_id, cv_document, job_offer,
messages}`) — **drop-in**, aucune modification backend.

## Tests (sans LLM)

```bash
python -m tests.test_adapter          # couche d'adaptation CV + offre
python -m tests.test_grids            # grilles déterministes D1-D6
python -m tests.test_orchestrator     # routage + anti-boucle
python -m tests.test_evaluator        # segmentation + conversion des signaux
python -m tests.test_adequation       # adéquation inclusive + positionnement
python -m tests.test_pipeline         # finalisation end-to-end (juge mocké)
python -m tests.test_non_regression   # snapshot anti-dérive des grilles
```

## Calibration & anti-biais (avec clé API)

```bash
python calibration.py <dossier_cas>   # moyenne ≤ 3,5 ? écart inter-groupes ?
```

Voir le plan complet : `Produit/SPEC_simulateur_entretien_v2.md` et le plan
d'implémentation associé.
