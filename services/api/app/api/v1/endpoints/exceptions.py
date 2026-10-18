from fastapi import APIRouter

from app.api.deps import CurrentTenant, DbSession
from app.schemas.read import CaseOut, ExceptionOut
from app.services import read

router = APIRouter()


@router.get("/exceptions", response_model=list[ExceptionOut])
def list_exceptions(db: DbSession, tenant: CurrentTenant) -> list[ExceptionOut]:
    return read.exceptions(db, tenant)


@router.get("/cases", response_model=list[CaseOut])
def list_cases(db: DbSession, tenant: CurrentTenant) -> list[CaseOut]:
    return read.cases(db, tenant)
