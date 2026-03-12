from fastapi import FastAPI

from app.api.mastery import router as mastery_router
from app.api.worksheets import router as worksheets_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(worksheets_router, prefix=settings.api_prefix)
app.include_router(mastery_router, prefix=settings.api_prefix)


@app.get("/")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
