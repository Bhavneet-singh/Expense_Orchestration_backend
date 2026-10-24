# Expense Orchestration Backend

A FastAPI and SQLAlchemy backend for sharing group expenses. It records who paid, calculates what each member owes, and provides read-only settlement suggestions.

## Project setup steps

### Run with Docker (recommended)

1. Copy the example environment file if you need to override the database URL:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Start the API and MySQL:

   ```powershell
   docker compose up --build
   ```

3. Open the API documentation at `http://localhost:8000/docs`.

The API is available on port `8000`. MySQL is exposed locally on port `3307` and is persisted in the Docker `mysql_data` volume.

### Run locally

1. Create and activate a virtual environment.
2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Ensure MySQL is running and set `DATABASE_URL` as shown in `.env.example`.
4. Start the server:

   ```powershell
   uvicorn app.main:app --reload
   ```

Run the test suite with `pytest`.

## Architecture overview

```text
app/
├── main.py                    # FastAPI app factory, startup, router registration
├── config.py                  # Environment-backed configuration
├── database.py                # SQLAlchemy engine, sessions, get_db dependency
├── models.py                  # SQLAlchemy database models
├── schemas.py                 # Pydantic request and response models
├── money.py                   # Decimal rupee <-> integer paise helpers
├── routers/                   # HTTP layer
│   ├── users.py
│   ├── groups.py
│   ├── expenses.py
│   ├── balances.py
│   └── settlements.py
└── services/                  # Framework-independent business logic
    ├── errors.py
    ├── expense_service.py
    ├── balance_service.py
    └── settlement_service.py

tests/                         # API and service-level tests
postman_collection.json        # Runnable API requests
```

```text
Client -> router -> Pydantic validation -> service -> SQLAlchemy models -> MySQL
       <- response schema      <- domain result <- database transaction
```

Routers parse HTTP input, obtain a database session, call a service, and translate known domain errors to HTTP responses. Services contain the expense, balance, and settlement rules without importing FastAPI, so they are independently unit-testable. Balances are derived from expenses and are never stored separately.

## API overview

All application routes begin with `/api`.

| Method | Endpoint | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/api/` | Health-style API check | 200 |
| POST | `/api/users` | Create a user | 201 |
| GET | `/api/users` | List users | 200 |
| GET | `/api/users/{user_id}` | Get one user | 200 |
| POST | `/api/groups` | Create a group | 201 |
| POST | `/api/groups/users` | Add a user to a group | 200 |
| GET | `/api/groups/{group_id}/users` | Get a group and its members | 200 |
| POST | `/api/expenses` | Record an expense and equal splits | 201 |
| GET | `/api/expenses` | List expenses | 200 |
| GET | `/api/groups/{group_id}/balances` | Calculate pairwise balances | 200 |
| GET | `/api/groups/{group_id}/settlements/suggestions` | Suggest settlement payments | 200 |

Example expense request:

```json
{
  "group_id": 1,
  "paid_by": 1,
  "amount": 1200.00,
  "description": "Dinner"
}
```

Interactive Swagger UI documentation is at `/docs`, ReDoc is at `/redoc`, and
the generated OpenAPI JSON is at `/openapi.json`. These are served by FastAPI,
not OpenAI. See [API Documentation](./API_DOCUMENTATION.md) for endpoint
details and examples. The included Postman collection uses `{{base_url}}`,
defaulting to `http://localhost:8000`.

## Database design explanation

For the detailed table and relationship reference, see [Database Schema Explanation](./DATABASE_SCHEMA.md).

MySQL holds four related tables. IDs are auto-incrementing integers and money is stored as fixed-precision `NUMERIC(12, 2)`, not binary floating point.

| Table | Purpose | Key relationships |
| --- | --- | --- |
| `groups` | An expense-sharing group, such as “Goa Trip”. | Has many users and expenses. |
| `users` | A participant. | Has an optional `group_id`; may pay expenses and owe splits. |
| `expenses` | One payment, including payer, total amount, and description. | Belongs to one group and one payer. |
| `expense_splits` | A non-payer member's portion of an expense. | Belongs to one expense and one user. |

```text
Group 1 ── * User
Group 1 ── * Expense
User  1 ── * Expense       (payer)
Expense 1 ─ * ExpenseSplit
User  1 ── * ExpenseSplit  (member who owes)
```

`expense_splits` has a unique constraint on `(expense_id, user_id)`, preventing duplicate splits for one expense and user. Pairwise balances and net settlement positions are calculated from `expenses` plus `expense_splits`, avoiding duplicated, stale balance data.

## Assumptions made

- A user belongs to zero or one group because `users.group_id` is one nullable foreign key.
- An expense is split equally among all members of its group.
- The payer must belong to the expense's group.
- Only non-payers receive an `expense_splits` row; the payer's contribution is represented by the expense itself.
- Currency is INR. Settlement logic uses integer paise internally to keep arithmetic exact.
- Settlement suggestions are advisory only; the app does not yet record completed payments.

## Design decisions

- **Layered design:** HTTP-specific code is in `routers/`; reusable business logic is in `services/`.
- **Pydantic boundary:** request and response schemas define the API shape and reject invalid inputs before business processing.
- **Decimal storage:** `NUMERIC(12, 2)` preserves currency precision in MySQL.
- **Paise during netting:** settlement matching uses integer paise to avoid cumulative rounding errors.
- **Derived balances:** no balance table is maintained, preventing write-time synchronization errors.
- **Deterministic suggestions:** user IDs break settlement ties, so equivalent inputs produce stable output.

## Improvements you would make with more time

- Add authentication, authorization, and group membership roles.
- Support many-to-many membership so a user can join multiple groups.
- Support exact, percentage, and unequal expense splits.
- Allocate rounding remainders explicitly for cases such as ₹1,000 divided by three so splits always sum exactly to the original expense.
- Add pagination, filtering, date fields, and richer expense history.
- Add database migrations instead of relying on startup table creation and compatibility checks.
- Add a payment-recording workflow with an audit history.
- Add structured logging, health checks, rate limiting, and CI checks.
- For small groups, offer an exact settlement optimizer; the current greedy approach is efficient and deterministic but not always globally minimal.
