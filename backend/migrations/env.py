"""Alembic environment: resolves the database URL from the app config."""
import os
from logging.config import fileConfig

# Importing the app factory must not auto-create the schema: migrations own it.
os.environ.setdefault("DB_AUTO_CREATE", "0")

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import create_app
from extensions import db

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_app = create_app()
config.set_main_option("sqlalchemy.url", _app.config["SQLALCHEMY_DATABASE_URI"])
target_metadata = db.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
