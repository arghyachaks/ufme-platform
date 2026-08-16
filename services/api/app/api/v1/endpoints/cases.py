from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_cases() -> list[dict[str, str]]:
    return []
