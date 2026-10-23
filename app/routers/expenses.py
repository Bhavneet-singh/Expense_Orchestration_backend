from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Expense
from app.schemas import ExpenseCreate, ExpenseResponse
from app.services.errors import (
    ExpenseCreationFailed,
    GroupNotFound,
    InvalidExpenseAmount,
    InvalidPayerGroup,
    PayerNotFound,
)
from app.services.expense_service import create_expense as create_expense_service


router = APIRouter(prefix="/api")


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
    try:
        return create_expense_service(
            db,
            expense.group_id,
            expense.paid_by,
            expense.amount,
            expense.description,
        )
    except GroupNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    except PayerNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payer not found",
        )
    except InvalidPayerGroup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payer must be a member of the expense group",
        )
    except InvalidExpenseAmount:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Input should be greater than 0",
        )
    except ExpenseCreationFailed:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Expense creation failed",
        )
