from fastapi import FastAPI
from sqlalchemy import inspect, text

from app.database import Base, engine
from app import models  # Registers SQLAlchemy models before creating tables.
from app.routers import balances, expenses, groups, settlements, users


def add_user_group_column_if_needed() -> None:
    """Apply the small schema change needed by databases created before groups."""
    if engine.dialect.name != "mysql":
        return

    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "group_id" in user_columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN group_id INTEGER NULL"))
        connection.execute(
            text(
                "ALTER TABLE users "
                "ADD CONSTRAINT fk_users_group_id "
                "FOREIGN KEY (group_id) REFERENCES groups (id)"
            )
        )
        connection.execute(
            text("CREATE INDEX ix_users_group_id ON users (group_id)")
        )


def create_app() -> FastAPI:
    application = FastAPI()

    @application.on_event("startup")
    def create_database_tables() -> None:
        Base.metadata.create_all(bind=engine)
        add_user_group_column_if_needed()

    @application.get("/api/")
    def api_root():
        return {"message": "API is running"}

    for router in (
        users.router,
        groups.router,
        expenses.router,
        balances.router,
        settlements.router,
    ):
        application.include_router(router)

    return application


app = create_app()
