from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import GroupBalanceMemberResponse
from app.services.balance_service import get_pairwise_balances
from app.services.errors import GroupNotFound


router = APIRouter(prefix="/api")


@router.get(
    "/groups/{group_id}/balances",
    response_model=dict[str, GroupBalanceMemberResponse],
)
def get_group_balances(group_id: int, db: Session = Depends(get_db)):
    try:
        return get_pairwise_balances(db, group_id)
    except GroupNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
