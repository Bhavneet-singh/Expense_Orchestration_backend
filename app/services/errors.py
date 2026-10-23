class GroupNotFound(Exception):
    """The requested group does not exist."""


class PayerNotFound(Exception):
    """The requested expense payer does not exist."""


class InvalidPayerGroup(Exception):
    """The expense payer is not a member of its group."""


class InvalidExpenseAmount(Exception):
    """Expense amounts must be positive."""


class ExpenseCreationFailed(Exception):
    """The database could not persist an expense."""

