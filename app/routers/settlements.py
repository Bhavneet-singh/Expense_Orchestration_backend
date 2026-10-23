from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SettlementSuggestionsResponse
from app.services.errors import GroupNotFound
from app.services.settlement_service import (
    get_settlement_suggestions as build_settlement_suggestions,
)


router = APIRouter(prefix="/api")


@router.get(
    "/groups/{group_id}/settlements/suggestions",
    response_model=SettlementSuggestionsResponse,
)
def get_settlement_suggestions(group_id: int, db: Session = Depends(get_db)):
    try:
        return build_settlement_suggestions(db, group_id)
    except GroupNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
