from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Manages application-wide settings and configurations."""

    stac_api_url: str = "http://localhost:8081"
    raster_api_url: str = "http://localhost:8082"
    tilejson_path: str = "WebMercatorQuad/tilejson.json"

    postgres_user: str = "username"
    postgres_pass: str = "password"  # noqa: S105
    postgres_host: str = "localhost"
    postgres_port: int = 5439
    postgres_dbname: str = "postgis"

    @computed_field
    def database_dsn(self) -> str:
        """Constructs the database DSN from individual components."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_pass}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_dbname}"
        )

    default_data_dir: Path = Path("data")
    files_to_load: list[str] = ["collections.json.zip", "items.json.zip"]

    map_layout: dict = {"height": "700px"}

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
