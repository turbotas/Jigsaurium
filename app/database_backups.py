from __future__ import annotations

import bz2
from datetime import date, datetime, time, timezone
from decimal import Decimal
import gzip
import json
from pathlib import Path
import re

from sqlalchemy import MetaData, select
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.db import Base


DEFAULT_BLOB_CHUNK_BYTES = 32 * 1024
DEFAULT_MAX_STATEMENT_BYTES = 4 * 1024 * 1024
DEFAULT_BACKUP_APP_NAME = "jigsaurium"
BACKUP_COMPRESSION_NONE = "none"
BACKUP_COMPRESSION_GZIP = "gzip"
BACKUP_COMPRESSION_BZIP2 = "bzip2"
SUPPORTED_BACKUP_COMPRESSIONS = {
    BACKUP_COMPRESSION_NONE,
    BACKUP_COMPRESSION_GZIP,
    BACKUP_COMPRESSION_BZIP2,
}

_NON_SAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _escape_sql_string(value: str) -> str:
    escaped = []
    for char in value:
        if char == "\\":
            escaped.append("\\\\")
        elif char == "'":
            escaped.append("\\'")
        elif char == "\0":
            escaped.append("\\0")
        elif char == "\n":
            escaped.append("\\n")
        elif char == "\r":
            escaped.append("\\r")
        elif char == "\t":
            escaped.append("\\t")
        elif char == "\b":
            escaped.append("\\b")
        elif char == "\x1a":
            escaped.append("\\Z")
        else:
            escaped.append(char)
    return "".join(escaped)


def _normalize_filename_token(value: str, *, fallback: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return fallback
    normalized = _NON_SAFE_FILENAME_CHARS.sub("-", raw).strip("-._")
    return normalized or fallback


def normalize_environment_label(app_env: str) -> str:
    normalized = _normalize_filename_token(app_env, fallback="dev")
    if normalized == "prod":
        return "live"
    return normalized


def normalize_backup_compression(value: str, *, default: str = BACKUP_COMPRESSION_GZIP) -> str:
    normalized = _normalize_filename_token(value, fallback=default)
    if normalized in {"bz2", "bzip"}:
        normalized = BACKUP_COMPRESSION_BZIP2
    if normalized not in SUPPORTED_BACKUP_COMPRESSIONS:
        return default
    return normalized


def _backup_file_extension(compression: str) -> str:
    if compression == BACKUP_COMPRESSION_NONE:
        return ".sql"
    if compression == BACKUP_COMPRESSION_BZIP2:
        return ".sql.bz2"
    return ".sql.gz"


def build_backup_filename(*, app_name: str, app_env: str, app_version: str, generated_at: datetime, compression: str) -> str:
    safe_name = _normalize_filename_token(app_name, fallback=DEFAULT_BACKUP_APP_NAME)
    safe_env = normalize_environment_label(app_env)
    safe_version = _normalize_filename_token(app_version, fallback="0.0.0")
    timestamp = generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{safe_name}-{safe_env}-v{safe_version}-{timestamp}{_backup_file_extension(compression)}"


def resolve_backup_root_path(*, app_instance_path: str, configured_path: str) -> Path:
    configured = str(configured_path or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(app_instance_path) / "backups").resolve()


def _format_datetime_literal(value: datetime) -> str:
    resolved = value
    if resolved.tzinfo is None:
        resolved = resolved.replace(tzinfo=timezone.utc)
    else:
        resolved = resolved.astimezone(timezone.utc)
    text = resolved.strftime("%Y-%m-%d %H:%M:%S.%f").rstrip("0").rstrip(".")
    return f"'{text}'"


def _format_time_literal(value: time) -> str:
    text = value.strftime("%H:%M:%S.%f").rstrip("0").rstrip(".")
    return f"'{text}'"


def _format_bytes_literal(value: bytes, *, chunk_bytes: int, blob_var_name: str, setup_statements: list[str]) -> str:
    if not value:
        return "UNHEX('')"

    hex_value = value.hex().upper()
    if len(value) <= chunk_bytes:
        return f"UNHEX('{hex_value}')"

    chunk_hex_length = max(2, int(chunk_bytes) * 2)
    chunks = [hex_value[index : index + chunk_hex_length] for index in range(0, len(hex_value), chunk_hex_length)]
    setup_statements.append(f"SET {blob_var_name} = UNHEX('{chunks[0]}');")
    for chunk in chunks[1:]:
        setup_statements.append(f"SET {blob_var_name} = CONCAT({blob_var_name}, UNHEX('{chunk}'));")
    return blob_var_name


def _format_sql_value(
    value,
    *,
    chunk_bytes: int,
    blob_var_name: str,
    setup_statements: list[str],
):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return _format_datetime_literal(value)
    if isinstance(value, date):
        return f"'{value.isoformat()}'"
    if isinstance(value, time):
        return _format_time_literal(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return _format_bytes_literal(bytes(value), chunk_bytes=chunk_bytes, blob_var_name=blob_var_name, setup_statements=setup_statements)
    if isinstance(value, (list, dict)):
        return f"'{_escape_sql_string(json.dumps(value, ensure_ascii=False))}'"
    return f"'{_escape_sql_string(str(value))}'"


def _build_insert_statements_for_row(
    table,
    row_mapping,
    *,
    row_number: int,
    blob_chunk_bytes: int,
    max_statement_bytes: int,
) -> list[str]:
    column_names = [column.name for column in table.columns]
    setup_statements: list[str] = []
    value_literals = []
    blob_counter = 0

    for column_name in column_names:
        value = row_mapping[column_name]
        blob_var_name = f"@blob_{table.name}_{row_number}_{blob_counter}"
        literal = _format_sql_value(
            value,
            chunk_bytes=blob_chunk_bytes,
            blob_var_name=blob_var_name,
            setup_statements=setup_statements,
        )
        if literal == blob_var_name:
            blob_counter += 1
        value_literals.append(literal)

    insert_sql = (
        f"INSERT INTO `{table.name}` ({', '.join(f'`{name}`' for name in column_names)}) "
        f"VALUES ({', '.join(value_literals)});"
    )
    if len(insert_sql.encode("utf-8")) > int(max_statement_bytes):
        raise RuntimeError(
            f"Backup export statement for table '{table.name}' row #{row_number} exceeds "
            f"DB_BACKUP_MAX_STATEMENT_BYTES ({max_statement_bytes})."
        )

    statements = []
    if setup_statements:
        statements.extend(setup_statements)
    statements.append(insert_sql)
    return statements


def _iter_ordered_tables(engine):
    reflected_metadata = MetaData()
    reflected_metadata.reflect(bind=engine)

    reflected_table_by_name = {
        table_name: table
        for table_name, table in reflected_metadata.tables.items()
        if not str(table_name).startswith("sqlite_")
    }
    reflected_names = set(reflected_table_by_name.keys())

    ordered_names = []
    for mapped_table in Base.metadata.sorted_tables:
        if mapped_table.name in reflected_names:
            ordered_names.append(mapped_table.name)
            reflected_names.discard(mapped_table.name)

    ordered_names.extend(sorted(reflected_names))
    return [reflected_table_by_name[name] for name in ordered_names]


def build_mysql_compatible_backup_sql(
    *,
    engine,
    app_name: str,
    app_env: str,
    app_version: str,
    generated_at: datetime,
    blob_chunk_bytes: int,
    max_statement_bytes: int,
) -> str:
    backup_name = build_backup_filename(
        app_name=app_name,
        app_env=app_env,
        app_version=app_version,
        generated_at=generated_at,
        compression=BACKUP_COMPRESSION_NONE,
    )
    export_lines = [
        f"-- {app_name} database backup",
        f"-- environment: {normalize_environment_label(app_env)}",
        f"-- version: {app_version}",
        f"-- generated_at_utc: {generated_at.astimezone(timezone.utc).isoformat()}",
        f"-- filename: {backup_name}",
        "",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS=0;",
        "",
    ]

    tables = _iter_ordered_tables(engine)
    with engine.connect() as connection:
        for table in tables:
            create_sql = str(CreateTable(table).compile(dialect=mysql.dialect()))
            if not create_sql.rstrip().endswith(";"):
                create_sql = f"{create_sql};"
            export_lines.append(f"DROP TABLE IF EXISTS `{table.name}`;")
            export_lines.append(create_sql)
            export_lines.append("")

        for table in tables:
            export_lines.append(f"-- data for `{table.name}`")
            order_columns = list(table.primary_key.columns)
            statement = select(table)
            if order_columns:
                statement = statement.order_by(*order_columns)
            rows = connection.execute(statement).mappings().all()
            if not rows:
                export_lines.append("")
                continue
            for row_index, row_mapping in enumerate(rows, start=1):
                export_lines.extend(
                    _build_insert_statements_for_row(
                        table,
                        row_mapping,
                        row_number=row_index,
                        blob_chunk_bytes=blob_chunk_bytes,
                        max_statement_bytes=max_statement_bytes,
                    )
                )
            export_lines.append("")

    export_lines.append("SET FOREIGN_KEY_CHECKS=1;")
    export_lines.append("")
    return "\n".join(export_lines)


def compress_backup_payload(sql_bytes: bytes, *, compression: str) -> bytes:
    resolved_compression = normalize_backup_compression(compression)
    if resolved_compression == BACKUP_COMPRESSION_NONE:
        return sql_bytes
    if resolved_compression == BACKUP_COMPRESSION_BZIP2:
        return bz2.compress(sql_bytes)
    return gzip.compress(sql_bytes)
