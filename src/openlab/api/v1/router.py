"""Aggregate v1 routers."""

from fastapi import APIRouter

from openlab.api.v1.genes import router as genes_router
from openlab.api.v1.genomes import router as genomes_router
from openlab.api.v1.evidence import router as evidence_router
from openlab.api.v1.hypotheses import router as hypotheses_router
from openlab.api.v1.usage import router as usage_router
from openlab.api.v1.validation import router as validation_router
from openlab.api.v1.simulation import router as simulation_router
from openlab.api.v1.population import router as population_router
from openlab.api.v1.settings import router as settings_router

router = APIRouter(prefix="/api/v1")
router.include_router(genes_router)
router.include_router(genomes_router)
router.include_router(evidence_router)
router.include_router(hypotheses_router)
router.include_router(usage_router)
router.include_router(validation_router)
router.include_router(simulation_router)
router.include_router(population_router)
router.include_router(settings_router)

# CellForge whole-cell simulation routes
from openlab.cellforge.api.routes.simulation import router as cf_sim_router
from openlab.cellforge.api.routes.annotation import router as cf_ann_router
from openlab.cellforge.api.routes.health import router as cf_health_router

from openlab.api.v1.agents import router as agents_router
router.include_router(agents_router)

from openlab.researchbook.api import router as researchbook_router
router.include_router(researchbook_router)

cellforge_router = APIRouter(prefix="/cellforge")
cellforge_router.include_router(cf_sim_router)
cellforge_router.include_router(cf_ann_router)
cellforge_router.include_router(cf_health_router)
router.include_router(cellforge_router)
