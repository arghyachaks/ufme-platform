from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_matches() -> list[dict[str, str]]:
    return []
