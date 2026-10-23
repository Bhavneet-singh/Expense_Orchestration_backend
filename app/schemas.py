
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    name: str


class UserResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class GroupCreate(BaseModel):
    name: str


class GroupResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class GroupUserAdd(BaseModel):
    group_id: int
    user_id: int


class GroupUsersResponse(GroupResponse):
    users: list[UserResponse]


class ExpenseCreate(BaseModel):
    group_id: int
    paid_by: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str


class ExpenseSplitResponse(BaseModel):
    user_id: int
    amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class ExpenseResponse(BaseModel):
    id: int
    group_id: int
    paid_by: int
    amount: Decimal
    description: str
    splits: list[ExpenseSplitResponse]

    model_config = ConfigDict(from_attributes=True)
