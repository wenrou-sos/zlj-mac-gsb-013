"""Create tables on startup and seed the demo scenario when the DB is empty."""
from sqlalchemy.orm import Session

from . import models
from .database import engine
from .seed import seed_database


def init_db(seed_if_empty: bool = True) -> None:
    models.Base.metadata.create_all(bind=engine)
    if seed_if_empty:
        from .database import SessionLocal

        db: Session = SessionLocal()
        try:
            if db.query(models.Flight).count() == 0:
                seed_database(db)
        finally:
            db.close()
