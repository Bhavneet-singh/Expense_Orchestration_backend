from collections.abc import Generator
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Expense, ExpenseSplit, Group, User
from app.schemas import (
    ExpenseCreate,
    ExpenseResponse,
    GroupCreate,
    GroupResponse,
    GroupUserAdd,
    GroupUsersResponse,
    UserCreate,
    UserResponse,
)

router = APIRouter(prefix="/api")


@router.get("/")
def api_root():
    return {"message": "API is running"}

#USER ROUTES 
# Create a session for each request and close it afterward.
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    try:
        new_user = User(name=user.name)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User Creation failed",
        )


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.get("/users", response_model=list[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()

# GROUP ROUTES
@router.post(
    "/groups",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    group: GroupCreate,
    db: Session = Depends(get_db),
):
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
def get_group_users(
    group_id: int,
    db: Session = Depends(get_db),
):
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    return group


# EXPENSE ROUTES
@router.get("/expenses", response_model=list[ExpenseResponse])
def get_all_expenses(db: Session = Depends(get_db)):
    return db.query(Expense).order_by(Expense.id).all()


@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_expense(
    expense: ExpenseCreate,
    db: Session = Depends(get_db),
):
    group = db.get(Group, expense.group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    payer = db.get(User, expense.paid_by)
    if payer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payer not found",
        )
    if payer.group_id != group.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payer must be a member of the expense group",
        )

    members = (
        db.query(User)
        .filter(User.group_id == group.id)
        .order_by(User.id)
        .all()
    )
    equal_share = (expense.amount / Decimal(len(members))).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    try:
        new_expense = Expense(
            group_id=group.id,
            paid_by=payer.id,
            amount=expense.amount,
            description=expense.description,
        )
        db.add(new_expense)
        db.flush()

        # The payer already covered their own share, so only other members owe money.
        for member in members:
            if member.id != payer.id:
                db.add(
                    ExpenseSplit(
                        expense_id=new_expense.id,
                        user_id=member.id,
                        amount=equal_share,
                    )
                )

        db.commit()
        db.refresh(new_expense)
        return new_expense
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Expense creation failed",
        )
