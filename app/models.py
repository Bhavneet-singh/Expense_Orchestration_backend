
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Group(Base):
    """A collection that can contain many users."""

    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    users = relationship("User", back_populates="group")
    expenses = relationship("Expense", back_populates="group")


class User(Base):
    """Database record for an application user."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True, index=True)
    group = relationship("Group", back_populates="users")
    paid_expenses = relationship(
        "Expense",
        back_populates="payer",
        foreign_keys="Expense.paid_by",
    )
    expense_splits = relationship("ExpenseSplit", back_populates="user")


class Expense(Base):
    """A payment made by one member of a group."""

    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    paid_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String(255), nullable=False)

    group = relationship("Group", back_populates="expenses")
    payer = relationship("User", back_populates="paid_expenses", foreign_keys=[paid_by])
    splits = relationship(
        "ExpenseSplit",
        back_populates="expense",
        cascade="all, delete-orphan",
    )


class ExpenseSplit(Base):
    """The amount a non-payer owes for an expense."""

    __tablename__ = "expense_splits"
    __table_args__ = (
        UniqueConstraint("expense_id", "user_id", name="uq_expense_split_user"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)

    expense = relationship("Expense", back_populates="splits")
    user = relationship("User", back_populates="expense_splits")
