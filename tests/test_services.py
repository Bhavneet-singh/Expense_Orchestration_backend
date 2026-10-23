from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import ExpenseSplit, Group, User
from app.services.balance_service import get_net_balances, get_pairwise_balances
from app.services.errors import GroupNotFound, InvalidExpenseAmount
from app.services.expense_service import create_expense


class ExpenseAndBalanceServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.group = Group(name="Goa Trip")
        self.session.add(self.group)
        self.session.flush()
        self.members = [
            User(name=name, group_id=self.group.id)
            for name in ("Mohit", "Rahul", "Ankit")
        ]
        self.session.add_all(self.members)
        self.session.commit()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_expense_creation_splits_equally_with_cent_rounding(self):
        expense = create_expense(
            self.session,
            self.group.id,
            self.members[0].id,
            Decimal("1000.00"),
            "Dinner",
        )

        self.assertEqual(
            [split.amount for split in expense.splits],
            [Decimal("333.33"), Decimal("333.33")],
        )

    def test_expense_creation_rejects_nonpositive_amount(self):
        with self.assertRaises(InvalidExpenseAmount):
            create_expense(
                self.session,
                self.group.id,
                self.members[0].id,
                Decimal("0"),
                "Dinner",
            )

    def test_expense_creation_rejects_unknown_group(self):
        with self.assertRaises(GroupNotFound):
            create_expense(
                self.session,
                self.group.id + 100,
                self.members[0].id,
                Decimal("1200.00"),
                "Dinner",
            )

    def test_balance_services_return_pairwise_and_net_balances(self):
        expense = create_expense(
            self.session,
            self.group.id,
            self.members[0].id,
            Decimal("1200.00"),
            "Dinner",
        )

        self.assertEqual(
            get_pairwise_balances(self.session, self.group.id),
            {
                "Rahul": {"owes": {"Mohit": Decimal("400.00")}},
                "Ankit": {"owes": {"Mohit": Decimal("400.00")}},
            },
        )
        self.assertEqual(
            get_net_balances(self.session, self.group.id),
            {
                self.members[0].id: 80_000,
                self.members[1].id: -40_000,
                self.members[2].id: -40_000,
            },
        )
        self.assertTrue(all(isinstance(split, ExpenseSplit) for split in expense.splits))

    def test_balance_services_reject_unknown_group(self):
        with self.assertRaises(GroupNotFound):
            get_pairwise_balances(self.session, self.group.id + 100)
        with self.assertRaises(GroupNotFound):
            get_net_balances(self.session, self.group.id + 100)


if __name__ == "__main__":
    unittest.main()
