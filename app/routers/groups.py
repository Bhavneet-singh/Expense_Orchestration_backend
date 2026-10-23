from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Group, User
from app.schemas import (
    GroupCreate,
    GroupResponse,
    GroupUserAdd,
    GroupUsersResponse,
    UserResponse,
)


router = APIRouter(prefix="/api")


@router.post(
    "/groups",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group(group: GroupCreate, db: Session = Depends(get_db)):
    try:
        new_group = Group(name=group.name)
        db.add(new_group)
        db.commit()
        db.refresh(new_group)
        return new_group
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Group creation failed",
        )


@router.post("/groups/users", response_model=UserResponse)
def add_user_to_group(
    membership: GroupUserAdd,
    db: Session = Depends(get_db),
):
    group = db.get(Group, membership.group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    user = db.get(User, membership.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        user.group_id = group.id
        db.commit()
        db.refresh(user)
        return user
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not add user to group",
        )


@router.get("/groups/{group_id}/users", response_model=GroupUsersResponse)
def get_group_users(group_id: int, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    return group
