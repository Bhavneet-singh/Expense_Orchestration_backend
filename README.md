## Smart Settlement Suggestions

Trips often end with a tangle of pairwise debts, and nobody wants to make six
separate payments. `GET /api/groups/{group_id}/settlements/suggestions` reduces
those debts to a small set of payments that clears the group balance.

The feature calculates each member's net balance, then greedily matches the
largest debtor and creditor. The database access and settlement logic are kept
separate: `app/services/settlement_service.py` has a pure suggestion function
that uses integer paise for money calculations and breaks ties deterministically
by user ID.

The greedy approach is fast and near-optimal in practice, but it is not always
the exact minimum number of payments; exact minimization is NP-hard. Suggestions
are read-only and never change expense data. They are scoped to one group because
netting across unrelated groups would be incorrect.

With more time, small groups could use exact subset-partitioning to find the true
minimum, and the API could add a "mark as paid" flow when settlements are made.

## Architecture overview / Project structure

```text
app/
  main.py
  config.py
  database.py
  models.py
  schemas.py
  money.py
  routers/
    users.py
    groups.py
    expenses.py
    balances.py
    settlements.py
  services/
    expense_service.py
    balance_service.py
    settlement_service.py
tests/
```

Routers are thin and services hold business logic without FastAPI imports, making
services unit-testable; balances are derived from expenses and are never stored.

## API documentation

Interactive API documentation is generated from the FastAPI OpenAPI schema:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

All application endpoints are under `/api`. JSON request examples and a
`{{base_url}}` variable are also available in `postman_collection.json`.

| Method | Endpoint | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/api/` | Check that the API is running | 200 |
| POST | `/api/users` | Create a user (`{"name":"Mohit"}`) | 201 |
| GET | `/api/users` | List users | 200 |
| GET | `/api/users/{user_id}` | Get one user | 200 |
| POST | `/api/groups` | Create a group (`{"name":"Goa Trip"}`) | 201 |
| POST | `/api/groups/users` | Add a user to a group (`{"group_id":1,"user_id":1}`) | 200 |
| GET | `/api/groups/{group_id}/users` | Get a group and its users | 200 |
| POST | `/api/expenses` | Create an expense | 201 |
| GET | `/api/expenses` | List expenses | 200 |
| GET | `/api/groups/{group_id}/balances` | Get derived pairwise balances | 200 |
| GET | `/api/groups/{group_id}/settlements/suggestions` | Suggest payments to settle net balances | 200 |

An expense request has the shape:

```json
{
  "group_id": 1,
  "paid_by": 1,
  "amount": 1200,
  "description": "Dinner"
}
```

Expense amounts must be positive and have at most two decimal places. The payer
must belong to the selected group. Unknown users, groups, or payers return 404;
an expense payer outside the group returns 400, and invalid request data returns
422. See OpenAPI or the Postman collection for response schemas and examples.

## Database schema

The database has four tables. Primary keys are auto-incrementing integer IDs;
foreign keys connect related records. Expense amounts and split amounts use
`NUMERIC(12, 2)`, so rupee values are stored as fixed-precision decimals rather
than binary floating-point numbers.

| Table | Main columns | Relationships and purpose |
| --- | --- | --- |
| `groups` | `id`, `name` | A group has many users and expenses. |
| `users` | `id`, `name`, nullable `group_id` | A user may belong to one group; they can pay expenses and owe expense splits. |
| `expenses` | `id`, `group_id`, `paid_by`, `amount`, `description` | Each expense belongs to a group and identifies its payer. |
| `expense_splits` | `id`, `expense_id`, `user_id`, `amount` | Stores each non-payer member's share of an expense. A unique constraint prevents duplicate splits for the same expense/user pair. |

`expenses.group_id`, `expenses.paid_by`, `expense_splits.expense_id`, and
`expense_splits.user_id` reference their associated group, payer, expense, and
user. Users and groups are not duplicated into the split rows: balances are
calculated from the recorded splits and payer, and are not persisted as a
separate table.
