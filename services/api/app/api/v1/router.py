from fastapi import APIRouter

from app.api.v1.endpoints import cases, health, matches, policies, rules

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(matches.router, prefix="/matches", tags=["matches"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
api_router.include_router(policies.router, prefix="/policies", tags=["policies"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
