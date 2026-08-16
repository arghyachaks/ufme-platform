from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_policies() -> list[dict[str, str]]:
    return []
