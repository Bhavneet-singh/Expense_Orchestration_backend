from decimal import Decimal

from sqlalchemy.orm import Session, selectinload

from app.models import Expense, Group, User
from app.money import to_paise
from app.services.errors import GroupNotFound


def get_pairwise_balances(
    db: Session,
    group_id: int,
) -> dict[str, dict[str, dict[str, Decimal]]]:
    """Return simplified member-to-member balances for one group."""
    group = db.get(Group, group_id)
    if group is None:
        raise GroupNotFound

    members = (
        db.query(User)
        .filter(User.group_id == group.id)
        .order_by(User.id)
        .all()
    )
    balances = {member.id: Decimal("0.00") for member in members}
    expenses = (
        db.query(Expense)
        .filter(Expense.group_id == group.id)
        .options(selectinload(Expense.splits))
        .order_by(Expense.id)
        .all()
    )

    for expense in expenses:
        for split in expense.splits:
            balances[split.user_id] -= split.amount
            balances[expense.paid_by] += split.amount

    debtors = [
        (member_id, -balance)
        for member_id, balance in balances.items()
        if balance < 0
    ]
    creditors = [
        (member_id, balance)
        for member_id, balance in balances.items()
        if balance > 0
    ]
    settlements: dict[int, dict[int, Decimal]] = {
        member.id: {} for member in members
    }
    debtor_index = 0
    creditor_index = 0

    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor_id, debt = debtors[debtor_index]
        creditor_id, credit = creditors[creditor_index]
        transfer = min(debt, credit)
        settlements[debtor_id][creditor_id] = transfer
        debtors[debtor_index] = (debtor_id, debt - transfer)
        creditors[creditor_index] = (creditor_id, credit - transfer)

        if debtors[debtor_index][1] == 0:
            debtor_index += 1
        if creditors[creditor_index][1] == 0:
            creditor_index += 1

    member_names = {member.id: member.name for member in members}
    return {
        member_names[member.id]: {
            "owes": {
                member_names[creditor_id]: amount
                for creditor_id, amount in settlements[member.id].items()
            }
        }
        for member in members
        if settlements[member.id]
    }


def get_net_balances(db: Session, group_id: int) -> dict[int, int]:
    """Return each current group member's net balance in integer paise."""
    group = db.get(Group, group_id)
    if group is None:
        raise GroupNotFound

    members = (
        db.query(User)
        .filter(User.group_id == group.id)
        .order_by(User.id)
        .all()
    )
    balances = {member.id: 0 for member in members}
    expenses = (
        db.query(Expense)
        .filter(Expense.group_id == group.id)
        .options(selectinload(Expense.splits))
        .all()
    )

    for expense in expenses:
        for split in expense.splits:
            balances.setdefault(split.user_id, 0)
            balances.setdefault(expense.paid_by, 0)
            amount_paise = to_paise(Decimal(split.amount))
            balances[split.user_id] -= amount_paise
            balances[expense.paid_by] += amount_paise

    return balances
