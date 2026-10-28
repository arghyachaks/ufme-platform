from fastapi import APIRouter

from app.api.v1.endpoints import ai, data, exceptions, health, platform, recon, rules, workflow

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(exceptions.router, tags=["exceptions & cases"])
api_router.include_router(rules.router, tags=["rules & policies"])
api_router.include_router(ai.router, tags=["ai"])
api_router.include_router(data.router, tags=["data & audit"])
api_router.include_router(platform.router, tags=["platform"])
api_router.include_router(recon.router, tags=["reconciliation"])
api_router.include_router(workflow.router, tags=["workflow"])
