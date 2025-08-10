import logging
import subprocess
import zipfile

import psycopg
from psycopg import sql

from eo_maxar.config import Settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class DataLoader:
    """Handles unzipping and loading STAC data into the pgSTAC database."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.data_path = self.settings.default_data_dir

    def run(self) -> None:
        """Executes the full data loading and configuration workflow."""
        logging.info("Starting data loading and setup process...")
        self._unzip_files()
        self._load_data_to_pgstac()
        self._configure_pgstac_context()
        logging.info("Data loading process completed successfully. ✅")

    def _unzip_files(self) -> None:
        """Unzips all required data files from the settings."""
        self.data_path.mkdir(exist_ok=True)
        for file_name in self.settings.files_to_load:
            zip_path = self.data_path / file_name
            if zip_path.exists():
                logging.info(f"Unzipping {zip_path}...")
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(self.data_path)
            else:
                logging.warning(f"File not found, skipping unzip: {zip_path}")

    def _load_data_to_pgstac(self) -> None:
        """Loads collections and items into pgSTAC using the pypgstac CLI."""
        for file_zip in self.settings.files_to_load:
            item_type = file_zip.split(".")[0]
            file_path = self.data_path / f"{item_type}.json"

            if not file_path.exists():
                logging.warning(
                    f"{item_type.capitalize()} file not found, skipping load: {file_path}"  # noqa: E501
                )
                continue

            logging.info(f"Loading {item_type} from {file_path} into pgSTAC...")

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
                logging.error(error_message)
                raise RuntimeError(error_message)
            else:
                logging.info(f"Successfully loaded {item_type}.")
                if result.stdout:
                    logging.debug(f"pypgstac stdout: {result.stdout}")

    def _configure_pgstac_context(self) -> None:
        """Connects to the database to enable the pgstac context setting."""
        logging.info("Configuring pgSTAC 'context' setting...")
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
            logging.info("Successfully enabled pgSTAC context.")
        except psycopg.Error as e:
            logging.exception(f"Database configuration failed: {e}")  # noqa: RUF100, TRY401
            raise
