"""Fixtures réalistes : un CVParsedFinal (parser v1.5) + une offre.

Profil volontairement atypique (reconversion pâtissier -> data analyst) pour
tester le cœur AIRH : compétences académiques à valider, capital transférable,
expérience non-tech valorisée.
"""

# Sortie réelle attendue du parser v1.5 (forme dict, comme transmise au backend).
CV_RECONVERSION_DATA: dict = {
    "candidat": {
        "first_name": "Sophie",
        "poste_vise_header": "Data Analyst",
        "introduction": "Reconvertie dans la data après 6 ans en pâtisserie, "
        "j'ai appris Python et SQL en autodidacte puis en bootcamp.",
        "is_reconversion": True,
        "is_etudiant": False,
        "is_disponible": True,
        "skills": {
            "hard_skills": [
                {"skill": "SQL", "context": "Bootcamp et projet personnel d'analyse de ventes"},
                {"skill": "Python", "context": "pandas utilisé sur projet dashboard ventes"},
                {"skill": "Power BI", "context": "Formation Data Analyst OpenClassrooms"},
                {"skill": "Java", "context": "Vu en cours pendant la formation, jamais utilisé depuis"},
                {"skill": "Statistiques", "context": "Notions de base acquises en formation"},
            ],
            "soft_skills": [
                {
                    "skill": "Gestion d'entreprise",
                    "context": "Gérante de sa propre pâtisserie pendant 4 ans",
                    "transferable": {"is_transferable": True, "applicabilite_tech": "Élevée"},
                },
                {
                    "skill": "Rigueur",
                    "context": "Respect strict des process en cuisine",
                    "transferable": {"is_transferable": True, "applicabilite_tech": "Moyenne"},
                },
                {
                    "skill": "Communication",
                    "context": "Relation client quotidienne",
                    "transferable": None,
                },
            ],
        },
        "experiences": [
            {
                "poste": "Gérante pâtisserie",
                "entreprise": "Les Délices de Sophie",
                "start_date": "2017-01",
                "end_date": "2021-06",
                "type": "professionnelle",
                "responsabilites_brutes": [
                    "Gestion des stocks et analyse des ventes hebdomadaires sur Excel",
                    "Pilotage de la trésorerie et des marges",
                ],
                "metriques_identifiees": ["CA 180k€/an", "réduction 15% pertes matières"],
                "evaluation_roni": {
                    "is_tech": False,
                    "note_soft_skills_valeur": 8,
                    "avis_roni": "Forte autonomie entrepreneuriale et habitude de "
                    "piloter des indicateurs chiffrés — transférable à l'analytics.",
                },
            },
            {
                "poste": "Projet bootcamp - Analyse de churn",
                "entreprise": "Le Wagon",
                "start_date": "2023-09",
                "end_date": "2023-12",
                "type": "projet_etudiant",
                "responsabilites_brutes": [
                    "Construction d'un pipeline SQL + Python pandas pour analyser le churn",
                    "Dashboard Power BI de restitution",
                ],
                "metriques_identifiees": ["dataset 50k lignes"],
                "evaluation_roni": {
                    "is_tech": True,
                    "note_coherence_tech": 7,
                    "avis_roni": "Bon premier projet data de bout en bout.",
                },
            },
        ],
        "projets": [
            {
                "title": "Dashboard ventes e-commerce",
                "technologies": ["SQL", "Python", "pandas", "Power BI"],
                "descriptif": ["Analyse de 2 ans de ventes", "KPIs et segmentation clients"],
                "avis_cto": "Projet complet, bonne maîtrise du cycle analytique.",
                "score_general_projet_pourcent": 72,
            }
        ],
        "formations": [
            {"titre_diplome": "Formation Data Analyst", "etablissement": "OpenClassrooms",
             "date_debut": "2022-09", "date_fin": "2023-06"},
        ],
        "langues": [{"langue": "Français", "niveau": "Maternelle"}],
        "certifications": [],
    },
    "recommandations_agentiques": {
        "profil_calcule_knowledge_graph": [
            {"nom": "Data Analyst", "confidence": 0.81},
            {"nom": "Business Intelligence Analyst", "confidence": 0.62},
        ],
        "production_readiness_score": 58,
        "contexte_recruteur": "Reconvertie crédible avec un projet data solide.",
        "axes_entretien_simulateur": [
            {
                "theme": "Transition pâtisserie vers data",
                "question_challenge": "Qu'est-ce qui t'a décidée à passer de la "
                "pâtisserie à la data, et comment t'es-tu formée ?",
                "competence_ciblee": "Motivation et trajectoire d'apprentissage",
            },
            {
                "theme": "Profondeur SQL",
                "question_challenge": "Sur ton projet churn, comment as-tu structuré "
                "tes requêtes SQL et pourquoi ces choix ?",
                "competence_ciblee": "SQL",
            },
            {
                "theme": "Gestion d'entreprise transférable",
                "question_challenge": "Quand tu pilotais tes marges, quels indicateurs "
                "suivais-tu et comment ?",
                "competence_ciblee": "Analyse d'indicateurs business",
            },
        ],
    },
}

OFFRE_DATA_ANALYST: dict = {
    "id": "job_123",
    "entreprise": "PME RetailCo",
    "ville": "Lille",
    "poste": "Data Analyst Junior",
    "contrat": "CDI",
    "mission": "Construire les tableaux de bord ventes et accompagner les "
    "équipes métier dans leurs décisions.",
    "profil_recherche": "Première expérience en data, maîtrise de SQL et d'un "
    "outil de BI, curiosité et sens du business.",
    "competences": "SQL, Power BI, Excel avancé, communication, statistiques descriptives",
    "pole": "Data",
}
