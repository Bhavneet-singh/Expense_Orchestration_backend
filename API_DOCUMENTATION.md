# API Documentation

The backend is a FastAPI application. Its API reference is generated from the
routes and Pydantic request/response models in the code:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

These are FastAPI's built-in OpenAPI documentation surfaces (Swagger UI and
ReDoc); they are **not managed by OpenAI**. The interactive pages are served by
the running API and reflect its current OpenAPI schema. This Markdown document
is the human-maintained guide. The project also includes a runnable
`postman_collection.json`.

Run the server locally with `uvicorn app.main:app --reload`, or follow the
Docker setup in the README. Unless otherwise stated, endpoints return JSON and
use the `/api` prefix.

## Endpoints

| Method | Path | Description | Success |
| --- | --- | --- | --- |
| GET | `/api/` | Check that the API is running. | 200 |
| POST | `/api/users` | Create a user. | 201 |
| GET | `/api/users` | List users ordered by ID. | 200 |
| GET | `/api/users/{user_id}` | Get one user. | 200 |
| POST | `/api/groups` | Create a group. | 201 |
| POST | `/api/groups/users` | Assign a user to a group. | 200 |
| GET | `/api/groups/{group_id}/users` | Get a group and its members. | 200 |
| POST | `/api/expenses` | Create an expense with equal shares. | 201 |
| GET | `/api/expenses` | List expenses ordered by ID. | 200 |
| GET | `/api/groups/{group_id}/balances` | Calculate pairwise amounts owed. | 200 |
| GET | `/api/groups/{group_id}/settlements/suggestions` | Generate read-only settlement suggestions. | 200 |

## Request and response examples

### Create a user

`POST /api/users`

```json
{
  "name": "Asha"
}
```

Response (`201 Created`):

```json
{
  "id": 1,
  "name": "Asha"
}
```

### Create a group

`POST /api/groups`

```json
{
  "name": "Goa Trip"
}
```

Response (`201 Created`):

```json
{
  "id": 1,
  "name": "Goa Trip"
}
```

### Add a user to a group

`POST /api/groups/users`

```json
{
  "group_id": 1,
  "user_id": 1
}
```

Response (`200 OK`) is the assigned user:

```json
{
  "id": 1,
  "name": "Asha"
}
```

### Read a group's members

`GET /api/groups/1/users`

Response (`200 OK`):

```json
{
  "id": 1,
  "name": "Goa Trip",
  "users": [
    {
      "id": 1,
      "name": "Asha"
    }
  ]
}
```

### Create an expense

`POST /api/expenses`

```json
{
  "group_id": 1,
  "paid_by": 1,
  "amount": 1200.00,
  "description": "Dinner"
}
```

`amount` must be greater than zero and may have at most two decimal places.
The payer must already belong to the selected group. The API divides the
expense equally among current group members and creates split rows for
non-payers.

Response (`201 Created`):

```json
{
  "id": 1,
  "group_id": 1,
  "paid_by": 1,
  "amount": "1200.00",
  "description": "Dinner",
  "splits": []
}
```

The `amount` and split `amount` values are decimal values and the active
FastAPI/Pydantic serializer returns them as JSON strings. The payer's expense
has no split row for themselves; with only one group member the `splits` array
is empty.

### Read pairwise balances

`GET /api/groups/1/balances`

Response (`200 OK`) contains only members who owe someone:

```json
{
  "Ravi": {
    "owes": {
      "Asha": 400.0
    }
  }
}
```

This is a simplified pairwise calculation derived from all expenses in the
group. Members with no outstanding debt are omitted. The response is keyed by
member names rather than IDs.

### Get settlement suggestions

`GET /api/groups/1/settlements/suggestions`

Response (`200 OK`):

```json
{
  "group_id": 1,
  "currency": "INR",
  "total_transactions": 1,
  "original_pairwise_count": 1,
  "suggestions": [
    {
      "from_user_id": 2,
      "from_user": "Ravi",
      "to_user_id": 1,
      "to_user": "Asha",
      "amount": 400.0
    }
  ]
}
```

Suggestions net the group's current positions and are advisory only; this
endpoint does not write payment or settlement records. Matching is deterministic
but greedy, so it is not guaranteed to produce a globally minimum number of
payments.

## Error responses

Errors use FastAPI's standard JSON shape, for example:

```json
{
  "detail": "Group not found"
}
```

Known cases include:

| Status | Example cause |
| --- | --- |
| 400 | Expense payer is not a member of the specified group. |
| 404 | Requested user or group does not exist. |
| 422 | Request body or path parameter fails validation; an expense amount is not positive or exceeds the supported precision. |
| 500 | A database write fails while creating a user, group, membership, or expense. |

## Notes and limitations

- List endpoints currently return all matching records; there is no pagination.
- A user can belong to one group at a time.
- Expense shares are equal; custom split amounts are not supported.
- Settlement suggestions do not represent completed payments.
- Request and response schemas are defined in `app/schemas.py`; route handlers
  are in `app/routers/`.
