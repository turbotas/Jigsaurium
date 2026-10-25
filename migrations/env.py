from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    load_dotenv = None

from app import models  # noqa: F401
from app.db import Base, ensure_sqlite_datetime_adapters
from config import Config

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

if load_dotenv is not None:
    load_dotenv()

configured_database_url = config.get_main_option("sqlalchemy.url")
env_database_url = os.getenv("DATABASE_URL")

if configured_database_url and configured_database_url != "sqlite+pysqlite:///:memory:":
    resolved_database_url = configured_database_url
elif env_database_url:
    resolved_database_url = env_database_url
elif configured_database_url:
    resolved_database_url = configured_database_url
else:
    resolved_database_url = Config.DATABASE_URL

config.set_main_option("sqlalchemy.url", resolved_database_url)

if resolved_database_url.startswith("sqlite"):
    ensure_sqlite_datetime_adapters()

if resolved_database_url == "sqlite+pysqlite:///:memory:":
    raise RuntimeError(
        "Alembic is targeting in-memory SQLite. Set DATABASE_URL (or provide --sqlalchemy-url) "
        "to run migrations against your actual environment database."
    )

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
