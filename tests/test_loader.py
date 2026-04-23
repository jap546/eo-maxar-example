"""Tests for DataLoader."""

import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eo_maxar.config import Settings
from eo_maxar.loader import DataLoader


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        default_data_dir=tmp_path,
        files_to_load=["collections.json.zip", "items.json.zip"],
        postgres_user="user",
        postgres_pass="pass",  # noqa: S106
        postgres_host="localhost",
        postgres_port=5432,
        postgres_dbname="testdb",
    )


@pytest.fixture
def loader(settings: Settings) -> DataLoader:
    return DataLoader(settings)


class TestItemTypeFromFilename:
    def test_collections_filename(self) -> None:
        assert (
            DataLoader._item_type_from_filename("collections.json.zip") == "collections"
        )

    def test_items_filename(self) -> None:
        assert DataLoader._item_type_from_filename("items.json.zip") == "items"

    def test_simple_filename(self) -> None:
        assert DataLoader._item_type_from_filename("data.zip") == "data"


class TestUnzipFiles:
    def test_unzips_existing_file(self, loader: DataLoader, tmp_path: Path) -> None:
        zip_path = tmp_path / "collections.json.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("collections.json", '{"type": "FeatureCollection"}')

        loader._unzip_files()

        assert (tmp_path / "collections.json").exists()

    def test_skips_missing_file(self, loader: DataLoader, tmp_path: Path) -> None:
        # No zip files exist — should log a warning but not raise
        loader._unzip_files()

    def test_creates_data_directory(self, loader: DataLoader, tmp_path: Path) -> None:
        new_dir = tmp_path / "newsubdir"
        loader.data_path = new_dir
        loader._unzip_files()
        assert new_dir.exists()


class TestLoadDataToPgstac:
    def test_runs_pypgstac_command(self, loader: DataLoader, tmp_path: Path) -> None:
        (tmp_path / "collections.json").write_text("{}")
        (tmp_path / "items.json").write_text("{}")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "some output"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            loader._load_data_to_pgstac()

        assert mock_run.call_count == 2
        first_call = mock_run.call_args_list[0][0][0]
        assert first_call[0] == "pypgstac"
        assert first_call[1] == "load"
        assert first_call[2] == "collections"

    def test_raises_on_nonzero_returncode(
        self, loader: DataLoader, tmp_path: Path
    ) -> None:
        (tmp_path / "collections.json").write_text("{}")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "out"
        mock_result.stderr = "err"

        with (
            patch("subprocess.run", return_value=mock_result),
            pytest.raises(RuntimeError, match="pypgstac failed"),
        ):
            loader._load_data_to_pgstac()

    def test_skips_missing_json_file(self, loader: DataLoader, tmp_path: Path) -> None:
        # No extracted .json files exist — should log warnings but not call subprocess
        with patch("subprocess.run") as mock_run:
            loader._load_data_to_pgstac()
        mock_run.assert_not_called()


class TestRun:
    def test_run_calls_all_steps(self, loader: DataLoader) -> None:
        with (
            patch.object(loader, "_unzip_files") as mock_unzip,
            patch.object(loader, "_load_data_to_pgstac") as mock_load,
            patch.object(loader, "_configure_pgstac_context") as mock_config,
        ):
            loader.run()
            mock_unzip.assert_called_once()
            mock_load.assert_called_once()
            mock_config.assert_called_once()


class TestConfigurePgstacContext:
    def test_executes_sql_query(self, loader: DataLoader) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = False
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = False

        with patch("psycopg.connect", return_value=mock_conn):
            loader._configure_pgstac_context()

        mock_cursor.execute.assert_called_once()
        assert "pgstac_settings" in str(mock_cursor.execute.call_args[0][0])

    def test_raises_on_db_error(self, loader: DataLoader) -> None:
        import psycopg as psycopg_lib

        with (
            patch(
                "psycopg.connect",
                side_effect=psycopg_lib.Error("connection error"),
            ),
            pytest.raises(psycopg_lib.Error),
        ):
            loader._configure_pgstac_context()

    def test_returns_true_when_db_reachable(self, loader: DataLoader) -> None:
        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        with patch("psycopg.connect", return_value=mock_conn):
            result = loader.health_check()
        assert result is True

    def test_returns_false_when_db_unreachable(self, loader: DataLoader) -> None:
        import psycopg as psycopg_lib

        with patch(
            "psycopg.connect",
            side_effect=psycopg_lib.OperationalError("connection refused"),
        ):
            result = loader.health_check()
        assert result is False
