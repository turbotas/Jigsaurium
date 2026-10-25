from datetime import datetime, timezone
import sqlite3
import warnings

import pytest

from app.db import ensure_sqlite_datetime_adapters


@pytest.mark.functional
def test_sqlite_datetime_adapter_registration_avoids_python312_deprecation_warning():
    ensure_sqlite_datetime_adapters()

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE sample_events (occurred_at TEXT NOT NULL)")
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "error",
                message=".*default datetime adapter is deprecated.*",
                category=DeprecationWarning,
            )
            connection.execute(
                "INSERT INTO sample_events (occurred_at) VALUES (?)",
                (datetime.now(timezone.utc),),
            )

        stored_value = connection.execute("SELECT occurred_at FROM sample_events").fetchone()[0]
        assert isinstance(stored_value, str)
        assert "+00:00" in stored_value
    finally:
        connection.close()
