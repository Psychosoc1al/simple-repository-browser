"""Tests for model timezone handling."""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import tempfile

from simple_repository_browser import fetch_projects, model


def test_SearchResultItem__from_db_row__converts_naive_to_utc():
    """Verify SearchResultItem.from_db_row() converts naive datetimes to UTC."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        con = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        con.row_factory = sqlite3.Row
        fetch_projects.create_table(con)

        # Insert with naive datetime (simulating what update_summary stores)
        naive_dt = datetime(2023, 1, 15, 12, 30, 0)
        con.execute(
            "INSERT INTO projects(canonical_name, preferred_name, summary, release_version, release_date) VALUES (?, ?, ?, ?, ?)",
            ("test-pkg", "Test-Pkg", "A test package", "1.0.0", naive_dt),
        )

        # Read back using from_db_row
        cursor = con.execute(
            "SELECT canonical_name, summary, release_version, release_date FROM projects WHERE canonical_name = ?",
            ("test-pkg",),
        )
        row = cursor.fetchone()
        result = model.SearchResultItem.from_db_row(row)

        # Should have UTC timezone
        assert result.canonical_name == "test-pkg"
        assert result.summary == "A test package"
        assert result.release_version == "1.0.0"
        assert result.release_date == datetime(
            2023, 1, 15, 12, 30, 0, tzinfo=timezone.utc
        )
        assert result.release_date.tzinfo is not None

        con.close()


def test_SearchResultItem__from_db_row__none_release_date() -> None:
    """Verify SearchResultItem.from_db_row() handles None release_date."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        con = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        con.row_factory = sqlite3.Row
        fetch_projects.create_table(con)

        fetch_projects.insert_if_missing(con, "test-pkg", "Test-Pkg")
        fetch_projects.update_summary(
            con,
            name="test-pkg",
            summary="A test package",
            release_date=None,
            release_version="1.0.0",
        )

        cursor = con.execute(
            "SELECT canonical_name, summary, release_version, release_date FROM projects WHERE canonical_name = ?",
            ("test-pkg",),
        )
        row = cursor.fetchone()
        result = model.SearchResultItem.from_db_row(row)

        assert result.canonical_name == "test-pkg"
        assert result.release_date is None
        con.close()
