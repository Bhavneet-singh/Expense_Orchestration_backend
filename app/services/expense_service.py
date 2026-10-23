from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Expense, ExpenseSplit, Group, User
from app.services.errors import (
    ExpenseCreationFailed,
    GroupNotFound,
    InvalidExpenseAmount,
    InvalidPayerGroup,
    PayerNotFound,
)


def create_expense(
    db: Session,
    group_id: int,
    paid_by: int,
    amount: Decimal,
    description: str,
) -> Expense:
    """Validate, split, and persist an expense with equal shares."""
    if amount <= 0:
        raise InvalidExpenseAmount

    group = db.get(Group, group_id)
    if group is None:
        raise GroupNotFound

    payer = db.get(User, paid_by)
    if payer is None:
        raise PayerNotFound
    if payer.group_id != group.id:
        raise InvalidPayerGroup

    members = (
        db.query(User)
        .filter(User.group_id == group.id)
        .order_by(User.id)
        .all()
    )
    equal_share = (amount / Decimal(len(members))).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    try:
        new_expense = Expense(
            group_id=group.id,
            paid_by=payer.id,
            amount=amount,
            description=description,
        )
        db.add(new_expense)
        db.flush()

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
    except SQLAlchemyError as error:
        db.rollback()
        raise ExpenseCreationFailed from error
