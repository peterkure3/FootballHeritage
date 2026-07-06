"""
Aggregates the domain routers under a single APIRouter.

Kept as the import point for api.main (`from api.routes import router`).
The actual endpoints live in api/routers/*.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import APIRouter

from api.routers.intelligence import router as intelligence_router
from api.routers.predictions import router as predictions_router
from api.routers.core import router as core_router
from api.routers.matchup import router as matchup_router
from api.routers.assistant import router as assistant_router
from api.routers.parlay import router as parlay_router
from api.routers.fpl import router as fpl_router
from api.routers.ncaab import router as ncaab_router

router = APIRouter()

router.include_router(intelligence_router)
router.include_router(predictions_router)
router.include_router(core_router)
router.include_router(matchup_router)
router.include_router(assistant_router)
router.include_router(parlay_router)
router.include_router(fpl_router)
router.include_router(ncaab_router)
