from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():

    return {

        "status": "ok",

        "project": settings.APP_NAME,

    }