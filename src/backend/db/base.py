"""SQLAlchemy declarative base.

All ORM models import ``Base`` from here. ``alembic/env.py`` imports
``Base.metadata`` for auto-migration detection.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
