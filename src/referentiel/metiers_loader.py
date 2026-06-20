"""Chargement du référentiel métier (metiers.json du parser).

Singleton : le fichier (~2.8 Mo) n'est chargé qu'une fois. On expose deux
lookups robustes (par nom exact/normalisé et par intitulé de poste libre) qui
renvoient une `FicheMetier` (sous-ensemble — on ignore les embeddings, inutiles
ici et coûteux en mémoire).

La résolution du chemin tolère plusieurs déploiements (env, copie locale,
module parser voisin) car les modules AIRH se déploient séparément.
"""

from __future__ import annotations

import json
import logging
import os
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

from src.core.config import DEFAULT_METIERS_PATH
from src.schemas.context_schema import FicheMetier

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Minuscule, sans accents, espaces compactés — pour matcher des libellés."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def _resolve_path() -> Optional[Path]:
    """Trouve metiers.json parmi les emplacements plausibles."""
    candidates: List[Path] = []
    if DEFAULT_METIERS_PATH:
        candidates.append(Path(DEFAULT_METIERS_PATH))
    here = Path(__file__).resolve()
    candidates.append(here.parent.parent / "data" / "metiers.json")  # copie locale
    # module parser voisin : IA/module_analyse_cv_v1.5/src/data/metiers.json
    ia_root = here.parents[3]  # .../IA
    candidates.append(ia_root / "module_analyse_cv_v1.5" / "src" / "data" / "metiers.json")
    candidates.append(ia_root / "cv_parser_api" / "src" / "data" / "metiers.json")

    for path in candidates:
        if path and path.is_file():
            return path
    logger.warning("metiers.json introuvable parmi: %s", [str(c) for c in candidates])
    return None


class MetiersReferentiel:
    """Accès indexé au référentiel métier."""

    _instance: Optional["MetiersReferentiel"] = None

    def __new__(cls) -> "MetiersReferentiel":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _ensure_loaded(self) -> None:
        if getattr(self, "_loaded", False):
            return
        self._by_nom: Dict[str, FicheMetier] = {}
        self._fiches: List[FicheMetier] = []

        path = _resolve_path()
        if path is None:
            self._loaded = True
            return

        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        for categorie in data.get("metiers", []):
            cat_nom = categorie.get("categorie")
            for metier in categorie.get("metiers", []):
                fiche = FicheMetier(
                    id=metier.get("id", _normalize(metier.get("nom", ""))),
                    nom=metier.get("nom", ""),
                    categorie=cat_nom,
                    description=metier.get("description"),
                    missions_principales=metier.get("missions_principales", []),
                    competences_techniques=metier.get("competences_techniques", []),
                    outils_technologies=metier.get("outils_technologies", []),
                    competences_soft=metier.get("competences_soft", []),
                    skills_atomic=metier.get("skills_atomic", []),
                    niveau_etude=metier.get("niveau_etude"),
                )
                self._fiches.append(fiche)
                self._by_nom[_normalize(fiche.nom)] = fiche

        logger.info("Référentiel métier chargé : %d fiches.", len(self._fiches))
        self._loaded = True

    # -- API publique -------------------------------------------------------- #

    def find_by_nom(self, nom: Optional[str]) -> Optional[FicheMetier]:
        """Lookup par nom exact (normalisé)."""
        self._ensure_loaded()
        if not nom:
            return None
        return self._by_nom.get(_normalize(nom))

    def find_by_poste(self, poste: Optional[str]) -> Optional[FicheMetier]:
        """Lookup tolérant depuis un intitulé de poste libre (offre).

        Stratégie : nom exact, puis inclusion de tokens significatifs
        (ex. "Data Analyst Junior H/F" -> "Data Analyst").
        """
        self._ensure_loaded()
        if not poste:
            return None
        exact = self.find_by_nom(poste)
        if exact:
            return exact

        norm_poste = _normalize(poste)
        best: Optional[FicheMetier] = None
        best_len = 0
        for key, fiche in self._by_nom.items():
            if key and key in norm_poste and len(key) > best_len:
                best, best_len = fiche, len(key)
        return best

    def resolve(
        self, metier_cible: Optional[str], poste: Optional[str]
    ) -> Optional[FicheMetier]:
        """Choisit la fiche : d'abord le métier calculé par le KG, sinon l'offre."""
        return self.find_by_nom(metier_cible) or self.find_by_poste(poste)


def get_referentiel() -> MetiersReferentiel:
    return MetiersReferentiel()
