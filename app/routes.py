from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/")
def api_root():
    return {"message": "API is running"}

# User Get route 