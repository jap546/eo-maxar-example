import logging
import subprocess
import zipfile
from pathlib import Path

import psycopg
from psycopg import sql

from eo_maxar.config import Settings

logger = logging.getLogger(__name__)


class DataLoader:
    """Handles unzipping and loading STAC data into the pgSTAC database."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.data_path = self.settings.default_data_dir

    def health_check(self) -> bool:
        """Verify the database is reachable before attempting to load.

        Returns:
            True if the database responds, False otherwise.
        """
        try:
            with psycopg.connect(self.settings.database_dsn) as conn:
                conn.execute("SELECT 1")
            return True
        except psycopg.Error as e:
            logger.error("Database health check failed: %s", e)
            return False

    def run(self) -> None:
        """Executes the full data loading and configuration workflow."""
        logger.info("Starting data loading and setup process...")
        self._unzip_files()
        self._load_data_to_pgstac()
        self._configure_pgstac_context()
        logger.info("Data loading process completed successfully.")

    def _unzip_files(self) -> None:
        """Unzips all required data files from the settings."""
        self.data_path.mkdir(exist_ok=True)
        for file_name in self.settings.files_to_load:
            zip_path = self.data_path / file_name
            if zip_path.exists():
                logger.info("Unzipping %s...", zip_path)
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(self.data_path)
            else:
                logger.warning("File not found, skipping unzip: %s", zip_path)

    @staticmethod
    def _item_type_from_filename(file_zip: str) -> str:
        """Extract the pgSTAC item type (e.g. 'collections', 'items') from a filename.

        Args:
            file_zip: Filename such as ``"collections.json.zip"``.

        Returns:
            The base name before the first dot, e.g. ``"collections"``.
        """
        return Path(file_zip).name.split(".")[0]

    def _load_data_to_pgstac(self) -> None:
        """Loads collections and items into pgSTAC using the pypgstac CLI."""
        for file_zip in self.settings.files_to_load:
            item_type = self._item_type_from_filename(file_zip)
            file_path = self.data_path / f"{item_type}.json"

            if not file_path.exists():
                logger.warning(
                    "%s file not found, skipping load: %s",
                    item_type.capitalize(),
                    file_path,
                )
                continue

            logger.info("Loading %s from %s into pgSTAC...", item_type, file_path)

            command = [
                "pypgstac",
                "load",
                item_type,
                str(file_path),
                "--dsn",
                self.settings.database_dsn,
                "--method",
                "insert_ignore",
            ]

            result = subprocess.run(  # noqa: S603
                command, capture_output=True, text=True, check=False
            )

            if result.returncode != 0:
                error_message = (
                    f"pypgstac failed for {file_path}.\n"
                    f"Stdout: {result.stdout}\n"
                    f"Stderr: {result.stderr}"
                )
                logger.error(error_message)
                raise RuntimeError(error_message)

            logger.info("Successfully loaded %s.", item_type)
            if result.stdout:
                logger.debug("pypgstac stdout: %s", result.stdout)

    def _configure_pgstac_context(self) -> None:
        """Connects to the database to enable the pgstac context setting."""
        logger.info("Configuring pgSTAC 'context' setting...")
        try:
            with (
                psycopg.connect(
                    self.settings.database_dsn,
                    autocommit=True,
                    options="-c search_path=pgstac,public -c application_name=pgstac",
                ) as conn,
                conn.cursor() as cursor,
            ):
                pgstac_settings_sql = """
                    INSERT INTO pgstac_settings (name, value)
                    VALUES ('context', 'on')
                    ON CONFLICT (name) DO UPDATE SET value = excluded.value;
                """
                cursor.execute(sql.SQL(pgstac_settings_sql))
            logger.info("Successfully enabled pgSTAC context.")
        except psycopg.Error as e:
            logger.exception("Database configuration failed: %s", e)
            raise
