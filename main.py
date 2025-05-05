import subprocess
import zipfile

import psycopg
from psycopg import sql

from eo_maxar.constants import Paths


def setup() -> None:
    """Wrapper to unzip data and load into local pgstac database."""
    for file in [
        "collections.json.zip",
        "items.json.zip",
    ]:
        path = Paths.DEFAULT_DATA_DIR
        with zipfile.ZipFile(path / file, "r") as zip_ref:
            zip_ref.extractall(path)
        item_type = file.split(".", maxsplit=1)[0]
        filename = file[:-4]

        command = [
            "pypgstac",
            "load",
            item_type,
            str(path / filename),
            "--dsn",
            "postgresql://username:password@0.0.0.0:5439/postgis",
            "--method",
            "insert_ignore",
        ]

        result = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            msg = (
                f"pypgstac failed for {filename}.\n"
                f"Stdout: {result.stdout}\n"
                f"Stderr: {result.stderr}"
            )
            raise RuntimeError(msg)

    with (
        psycopg.connect(
            "postgresql://username:password@0.0.0.0:5439/postgis",
            autocommit=True,
            options="-c search_path=pgstac,public -c application_name=pgstac",
        ) as conn,
        conn.cursor() as cursor,
    ):
        pgstac_settings = """
            INSERT INTO pgstac_settings (name, value)
            VALUES ('context', 'on')
            ON CONFLICT ON CONSTRAINT pgstac_settings_pkey DO UPDATE SET value = excluded.value;"""  # noqa: E501
        cursor.execute(sql.SQL(pgstac_settings))
