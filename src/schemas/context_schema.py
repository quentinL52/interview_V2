"""Schémas du contexte d'entretien — le contrat d'entrée du simulateur.

Trois objets normalisés, produits par la couche d'adaptation :
- `ProfilCandidat`  : dérivé de `CVParsedFinal` (parser v1.5) ;
- `AttendusPoste`   : dérivé de l'offre d'emploi (JobOffer) ;
- `InterviewContext`: fusion profil + attendus + fiche métier.

Ces objets découplent le simulateur du format exact du parser : si le parser
évolue, seuls les adapters changent, pas le graph ni le scoring.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
#  Profil candidat (dérivé du parser v1.5)
# --------------------------------------------------------------------------- #

class SkillEval(BaseModel):
    """Compétence technique avec son niveau de maîtrise dérivé."""
    nom: str
    contexte: str = ""
    # declare < academique < projet < production (échelle parser v2)
    niveau_maitrise: str = "declare"
    # Priorité de validation en entretien (skill flou ou critique non prouvé).
    a_valider_entretien: bool = False
    # Vrai si l'offre attend cette compétence (croisé avec AttendusPoste).
    critique_offre: bool = False


class SoftSkillEval(BaseModel):
    nom: str
    contexte: str = ""


class CompetenceTransferable(BaseModel):
    """Capital acquis hors tech, potentiellement applicable au poste (D4)."""
    source: str = ""                      # expérience / contexte d'origine
    competence: str
    certitude: str = "flou"               # flou < probable < confirme
    applicabilite_tech: str = "moyenne"   # faible / moyenne / elevee
    note: str = ""


class ProjetResume(BaseModel):
    title: str
    technologies: List[str] = Field(default_factory=list)
    score_pourcent: Optional[int] = None  # score parser (axe_complexite, etc.)
    avis_cto: Optional[str] = None


class AxeEntretienPriorise(BaseModel):
    """Axe d'entretien issu du parser, routé vers l'agent compétent."""
    agent: str                            # icebreaker/auditeur/enqueteur/stratege/projecteur
    theme: str
    question_guide: str = ""
    competence_ciblee: str = ""
    niveau_urgence: str = "moyenne"       # haute / moyenne / faible


class ProfilCandidat(BaseModel):
    first_name: str = "Candidat"
    poste_vise: Optional[str] = None
    introduction: Optional[str] = None

    is_reconversion: bool = False
    is_etudiant: bool = False
    is_disponible: Optional[bool] = None

    hard_skills: List[SkillEval] = Field(default_factory=list)
    soft_skills: List[SoftSkillEval] = Field(default_factory=list)
    competences_transferables: List[CompetenceTransferable] = Field(default_factory=list)
    projets: List[ProjetResume] = Field(default_factory=list)

    # Métier dominant calculé par le knowledge graph du parser (top-1).
    metier_cible: Optional[str] = None
    metier_confidence: float = 0.0

    # Axes d'entretien priorisés, déjà routés par agent.
    axes_entretien: List[AxeEntretienPriorise] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
#  Attendus du poste (dérivé de l'offre d'emploi)
# --------------------------------------------------------------------------- #

class AttendusPoste(BaseModel):
    entreprise: Optional[str] = None
    poste: Optional[str] = None
    ville: Optional[str] = None
    contrat: Optional[str] = None
    pole: Optional[str] = None

    mission: Optional[str] = None
    profil_recherche: Optional[str] = None

    # Compétences attendues extraites de l'offre (string -> liste normalisée).
    competences_attendues: List[str] = Field(default_factory=list)
    # junior / confirme / senior, dérivé de l'offre.
    seniorite: str = "confirme"
    # Texte brut conservé pour contextualiser les prompts agents.
    contexte_brut: str = ""

    @property
    def is_fournie(self) -> bool:
        """Vrai si une offre exploitable a été fournie (cas nominal)."""
        return bool(self.poste or self.mission or self.competences_attendues)


# --------------------------------------------------------------------------- #
#  Fiche métier (sous-ensemble chargé du référentiel metiers.json)
# --------------------------------------------------------------------------- #

class FicheMetier(BaseModel):
    id: str
    nom: str
    categorie: Optional[str] = None
    description: Optional[str] = None
    missions_principales: List[str] = Field(default_factory=list)
    competences_techniques: List[str] = Field(default_factory=list)
    outils_technologies: List[str] = Field(default_factory=list)
    competences_soft: List[str] = Field(default_factory=list)
    skills_atomic: List[str] = Field(default_factory=list)
    niveau_etude: Optional[str] = None


# --------------------------------------------------------------------------- #
#  Contexte fusionné — entrée du graph d'entretien
# --------------------------------------------------------------------------- #

class InterviewContext(BaseModel):
    profil: ProfilCandidat
    attendus: AttendusPoste
    fiche_metier: Optional[FicheMetier] = None
    # Union des compétences critiques (offre + fiche métier), normalisées.
    skills_critiques: List[str] = Field(default_factory=list)
