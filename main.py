"""API du Simulateur d'Entretien v2 — drop-in du service existant.

Endpoint `POST /simulate-interview/` : même contrat que la v1
(payload {user_id, job_offer_id, cv_document, job_offer, messages}). La réponse
contient `response` (texte de Roni), `current_agent`, `status`, et, à la fin,
le `report` (SimulationReportV2).
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

load_dotenv()

from src.graph.orchestrator import InterviewProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AIRH — Simulateur d'Entretien v2",
    description="Simulateur ultra-spécialisé data/IA : conversation chaleureuse, "
    "évaluation déterministe par grilles D1-D6, rapports auditables.",
    version="2.0.0",
)

ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthCheck(BaseModel):
    status: str = "ok"
    version: str = "2.0.0"


@app.get("/", response_model=HealthCheck, tags=["Status"])
async def health_check():
    return HealthCheck()


@app.post("/simulate-interview/")
async def simulate_interview(request: Request):
    """Traite un tour d'entretien (ou finalise si le budget est atteint)."""
    try:
        payload = await request.json()
        required = ("user_id", "job_offer_id", "cv_document", "job_offer")
        if not all(k in payload for k in required):
            raise HTTPException(
                status_code=400,
                detail=f"Payload incomplet (requis : {', '.join(required)}).",
            )

        logger.info("Simulation pour user=%s", payload.get("user_id"))
        processor = InterviewProcessor(payload)
        result = processor.step(payload.get("messages", []))
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("Erreur de validation : %s", ve, exc_info=True)
        return JSONResponse(content={"error": str(ve)}, status_code=400)
    except Exception as exc:
        logger.error("Erreur interne : %s", exc, exc_info=True)
        return JSONResponse(
            content={"error": "Erreur interne du serveur d'entretien."},
            status_code=500,
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 7861))
    uvicorn.run(app, host="0.0.0.0", port=port)
