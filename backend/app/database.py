from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_application_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    required_columns = {
        "location": "VARCHAR(255)",
        "form_data": "JSON",
        "workflow": "JSON",
    }
    existing_columns = {column["name"] for column in inspect(engine).get_columns("service_applications")}
    missing_columns = required_columns.keys() - existing_columns

    if missing_columns:
        with engine.begin() as connection:
            for column_name in missing_columns:
                connection.execute(
                    text(f"ALTER TABLE service_applications ADD COLUMN {column_name} {required_columns[column_name]}")
                )


def ensure_user_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    existing_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if "department" not in existing_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN department VARCHAR(200)"))
