from eo_maxar.config import settings
from eo_maxar.loader import DataLoader


def setup() -> None:
    """
    Initializes and runs the data loader to set up the database.
    This function is the entry point for the 'setup' command.
    """
    loader = DataLoader(settings)
    loader.run()
