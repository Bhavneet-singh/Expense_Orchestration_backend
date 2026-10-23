import asyncio
import json
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database
from app.database import Base
from app.main import app
from app.services.settlement_service import suggest_settlements


class SettlementSuggestionTests(unittest.TestCase):
    def test_assignment_example(self):
        suggestions = suggest_settlements({1: 80_000, 2: -40_000, 3: -40_000})

        self.assertEqual(suggestions, [(2, 1, 40_000), (3, 1, 40_000)])

    def test_chain_collapses_to_one_payment(self):
        self.assertEqual(
            suggest_settlements({1: -10_000, 2: 0, 3: 10_000}),
            [(1, 3, 10_000)],
        )

    def test_suggestions_clear_each_hand_written_balance_set(self):
        cases = [
            {1: 80_000, 2: -40_000, 3: -40_000},
            {1: -8_000, 2: -2_000, 3: 5_000, 4: 5_000},
            {1: 0, 2: 0, 3: 0},
        ]

        for balances in cases:
            remaining = balances.copy()
            for from_user_id, to_user_id, amount in suggest_settlements(balances):
                remaining[from_user_id] += amount
                remaining[to_user_id] -= amount
            self.assertTrue(all(balance == 0 for balance in remaining.values()))

    def test_already_settled_returns_no_suggestions(self):
        self.assertEqual(suggest_settlements({1: 0, 2: 0}), [])

    def test_unbalanced_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            suggest_settlements({1: 100, 2: -99})

    def test_ties_are_deterministic_by_user_id(self):
        balances = {4: -100, 2: -100, 7: 100, 3: 100}

        self.assertEqual(
            suggest_settlements(balances),
            [(2, 3, 100), (4, 7, 100)],
        )

    def test_transaction_count_is_at_most_member_count_minus_one(self):
        balances = {1: -600, 2: -200, 3: -100, 4: 400, 5: 500}

        self.assertLessEqual(len(suggest_settlements(balances)), len(balances) - 1)


class SettlementSuggestionsApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        self.original_session_local = database.SessionLocal
        database.SessionLocal = self.session_local

    def tearDown(self):
        database.SessionLocal = self.original_session_local
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def request(self, method, path, body=None):
        payload = json.dumps(body).encode() if body is not None else b""
        messages = []
        request_received = False

        async def receive():
            nonlocal request_received
            if request_received:
                return {"type": "http.disconnect"}
            request_received = True
            return {"type": "http.request", "body": payload, "more_body": False}

        async def send(message):
            messages.append(message)

        headers = []
        if body is not None:
            headers.append((b"content-type", b"application/json"))
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": headers,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }
        asyncio.run(app(scope, receive, send))

        status = next(
            message["status"]
            for message in messages
            if message["type"] == "http.response.start"
        )
        response_body = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        return status, json.loads(response_body) if response_body else None

    def test_suggestions_endpoint_returns_group_settlement_plan(self):
        users = {}
        for name in ("Mohit", "Rahul", "Ankit"):
            status, users[name] = self.request("POST", "/api/users", {"name": name})
            self.assertEqual(status, 201)

        status, group = self.request("POST", "/api/groups", {"name": "Trip"})
        self.assertEqual(status, 201)
        for user in users.values():
            status, _ = self.request(
                "POST",
                "/api/groups/users",
                {"group_id": group["id"], "user_id": user["id"]},
            )
            self.assertEqual(status, 200)

        status, _ = self.request(
            "POST",
            "/api/expenses",
            {
                "group_id": group["id"],
                "paid_by": users["Mohit"]["id"],
                "amount": 1200,
                "description": "Hotel",
            },
        )
        self.assertEqual(status, 201)

        status, response = self.request(
            "GET", f"/api/groups/{group['id']}/settlements/suggestions"
        )

        self.assertEqual(status, 200)
        self.assertEqual(response["group_id"], group["id"])
        self.assertEqual(response["currency"], "INR")
        self.assertEqual(response["total_transactions"], 2)
        self.assertEqual(response["original_pairwise_count"], 2)
        self.assertEqual(
            response["suggestions"],
            [
                {
                    "from_user_id": users["Rahul"]["id"],
                    "from_user": "Rahul",
                    "to_user_id": users["Mohit"]["id"],
                    "to_user": "Mohit",
                    "amount": 400.0,
                },
                {
                    "from_user_id": users["Ankit"]["id"],
                    "from_user": "Ankit",
                    "to_user_id": users["Mohit"]["id"],
                    "to_user": "Mohit",
                    "amount": 400.0,
                },
            ],
        )

    def test_suggestions_endpoint_returns_404_for_unknown_group(self):
        status, response = self.request(
            "GET",
            "/api/groups/999/settlements/suggestions",
        )

        self.assertEqual(status, 404)
        self.assertEqual(response["detail"], "Group not found")


if __name__ == "__main__":
    unittest.main()
