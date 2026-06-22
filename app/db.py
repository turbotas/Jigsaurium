from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def init_db(app):
    engine = create_engine(app.config["DATABASE_URL"], pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = scoped_session(session_factory)

    app.extensions["sqlalchemy_engine"] = engine
    app.extensions["sqlalchemy_session"] = session

    @app.teardown_appcontext
    def shutdown_session(_exception=None):
        session.remove()


def get_engine(app=None):
    app = app or current_app
    return app.extensions["sqlalchemy_engine"]


def get_session(app=None):
    app = app or current_app
    return app.extensions["sqlalchemy_session"]
