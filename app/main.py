from fastapi import FastAPI

from app.database import Base, engine
from app import models  # Registers SQLAlchemy models before creating tables.
from app.routes import router

app = FastAPI()


@app.on_event("startup")
def create_database_tables() -> None:
    Base.metadata.create_all(bind=engine)


app.include_router(router)


