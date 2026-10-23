"""Read-only settlement suggestions for a single group.

Net balances are derived from expenses and their splits; no settlement records
are included or written. Integer paise keeps the matching arithmetic exact.
"""

import heapq
from typing import TypedDict

from sqlalchemy.orm import Session

from app.models import Expense, ExpenseSplit, User
from app.money import from_paise
from app.services.balance_service import get_net_balances


class SettlementSuggestion(TypedDict):
    from_user_id: int
    from_user: str
    to_user_id: int
    to_user: str
    amount: float


class SettlementSuggestions(TypedDict):
    group_id: int
    total_transactions: int
    original_pairwise_count: int
    suggestions: list[SettlementSuggestion]


def suggest_settlements(net_balances: dict[int, int]) -> list[tuple[int, int, int]]:
    """Greedily match debtors and creditors using integer paise.

    Each tuple is (debtor ID, creditor ID, amount in paise). The largest
    outstanding debt and credit are paired, and the smaller amount is settled;
    at least one side reaches zero on every iteration. For example, A owing B
    100 and B owing C 100 nets to one suggestion: A pays C 100.

    Heap ordering gives O(n log n) work and ascending user IDs break ties
    deterministically. The result uses at most n - 1 payments, but greedy
    matching is not guaranteed to find the absolute minimum, which is
    NP-hard to optimize in general.
    """
    if sum(net_balances.values()) != 0:
        raise ValueError("Net balances must sum to zero")

    debtors = [
        (balance, user_id)
        for user_id, balance in net_balances.items()
        if balance < 0
    ]
    creditors = [
        (-balance, user_id)
        for user_id, balance in net_balances.items()
        if balance > 0
    ]
    heapq.heapify(debtors)
    heapq.heapify(creditors)

    suggestions: list[tuple[int, int, int]] = []
    while debtors and creditors:
        negative_debt, debtor_id = heapq.heappop(debtors)
        negative_credit, creditor_id = heapq.heappop(creditors)
        debt = -negative_debt
        credit = -negative_credit
        amount = min(debt, credit)
        suggestions.append((debtor_id, creditor_id, amount))

        if debt > amount:
            heapq.heappush(debtors, (-(debt - amount), debtor_id))
        if credit > amount:
            heapq.heappush(creditors, (-(credit - amount), creditor_id))

    return suggestions


def get_settlement_suggestions(
    db: Session,
    group_id: int,
) -> SettlementSuggestions:
    """Build read-only suggestions and names for one group's current balances.

    Netting is group-scoped so obligations from unrelated groups never offset
    one another. Suggestions are advice only and do not update the database.
    """
    net_balances = get_net_balances(db, group_id)
    suggestions = suggest_settlements(net_balances)
    users = (
        db.query(User)
        .filter(User.id.in_(net_balances))
        .order_by(User.id)
        .all()
    )
    user_names = {user.id: user.name for user in users}
    original_pairwise_count = (
        db.query(ExpenseSplit)
        .join(Expense, ExpenseSplit.expense_id == Expense.id)
        .filter(Expense.group_id == group_id, ExpenseSplit.amount != 0)
        .count()
    )

    return {
        "group_id": group_id,
        "total_transactions": len(suggestions),
        "original_pairwise_count": original_pairwise_count,
        "suggestions": [
            {
                "from_user_id": from_user_id,
                "from_user": user_names[from_user_id],
                "to_user_id": to_user_id,
                "to_user": user_names[to_user_id],
                "amount": float(from_paise(amount_paise)),
            }
            for from_user_id, to_user_id, amount_paise in suggestions
        ],
    }
