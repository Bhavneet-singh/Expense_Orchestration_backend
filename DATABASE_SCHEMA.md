# Database Schema Explanation

The application uses MySQL with SQLAlchemy models defined in `app/models.py`.
Tables are created at application startup with `Base.metadata.create_all`; the
project does not currently use a migration tool. The database URL is configured
through `DATABASE_URL`.

## Entity relationship overview

```text
groups 1 ─── * users
groups 1 ─── * expenses
users  1 ─── * expenses        (payer)
expenses 1 ─ * expense_splits
users  1 ─── * expense_splits  (member who owes)
```

A user belongs to zero or one group. An expense belongs to one group and has one
user as its payer. Each `expense_splits` row records one non-payer member's
share of an expense. These relationships are enforced with foreign keys.

## Tables and columns

### `groups`

Stores expense-sharing groups.

| Column | Type | Null? | Details |
| --- | --- | --- | --- |
| `id` | `INTEGER` | No | Auto-incrementing primary key; indexed. |
| `name` | `VARCHAR(255)` | No | Group name. |

One group can be related to multiple users and expenses.

### `users`

Stores participants.

| Column | Type | Null? | Details |
| --- | --- | --- | --- |
| `id` | `INTEGER` | No | Auto-incrementing primary key; indexed. |
| `name` | `VARCHAR(255)` | No | User name. |
| `group_id` | `INTEGER` | Yes | Indexed foreign key to `groups.id`. A null value means the user has not joined a group. |

The single `group_id` column means users cannot belong to multiple groups in the
current schema. The API's add-member operation assigns the user to the selected
group.

### `expenses`

Stores payments made on behalf of a group.

| Column | Type | Null? | Details |
| --- | --- | --- | --- |
| `id` | `INTEGER` | No | Auto-incrementing primary key; indexed. |
| `group_id` | `INTEGER` | No | Indexed foreign key to `groups.id`. |
| `paid_by` | `INTEGER` | No | Indexed foreign key to `users.id`. |
| `amount` | `NUMERIC(12, 2)` | No | Expense total, stored as fixed-precision decimal currency. |
| `description` | `VARCHAR(255)` | No | Short description of the expense. |

The payer must be a member of the expense's group. The API creates equal
per-member shares and stores rows only for members other than the payer.
Shares are rounded to two decimal places using half-up rounding; because a
remainder is not separately allocated, rounded shares are not guaranteed to add
up exactly to the expense total for every group size.

### `expense_splits`

Stores the portion owed by a member for an expense.

| Column | Type | Null? | Details |
| --- | --- | --- | --- |
| `id` | `INTEGER` | No | Auto-incrementing primary key; indexed. |
| `expense_id` | `INTEGER` | No | Indexed foreign key to `expenses.id`. |
| `user_id` | `INTEGER` | No | Indexed foreign key to `users.id`. |
| `amount` | `NUMERIC(12, 2)` | No | The member's share of that expense. |

The pair `(expense_id, user_id)` has a unique constraint named
`uq_expense_split_user`, so a member can have at most one split row per
expense.

## How balances are represented

There is no balances or settlements table. Pairwise balances and settlement
suggestions are computed from expenses and their split rows when requested.
This avoids storing a second copy of financial state that could become stale.
Settlement suggestions are read-only advice; the application does not record
that a suggested payment was completed.

Money is stored as `NUMERIC(12, 2)`. Settlement netting converts values to
integer paise while calculating, avoiding floating-point arithmetic in the
matching algorithm.

## Schema lifecycle

At startup, SQLAlchemy creates missing tables. `app/main.py` also contains a
small MySQL-only compatibility step that adds `users.group_id` to an older
`users` table if needed. `create_all` does not alter existing tables generally;
use a migration system for future schema changes that need reliable upgrades.

See [API Documentation](./API_DOCUMENTATION.md) for the endpoints that read and
write this schema.
