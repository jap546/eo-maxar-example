import nox

# Global options
nox.options.sessions = ("ruff", "mypy", "bandit")
nox.options.reuse_existing_virtualenvs = True
SILENT_DEFAULT = True
SILENT_CODE_MODIFIERS = False

# Targets
PACKAGE_LOCATION = "."
CODE_LOCATIONS = PACKAGE_LOCATION
PYTHON_VERSIONS = ["3.12", "3.13"]
PYPY3_VERSION = "pypy3"
LATEST_PYTHON = PYTHON_VERSIONS[-1]


@nox.session(python=PYTHON_VERSIONS, tags=["lint", "format"])
def ruff(session: nox.Session) -> None:
    """Lint and format with ruff."""
    args = session.posargs or (PACKAGE_LOCATION,)
    _install(session, "ruff")
    _run(session, "ruff", "check", *args)
    _run_code_modifier(session, "ruff", "format", *args)


@nox.session(python=PYTHON_VERSIONS, tags=["typecheck"])
def mypy(session: nox.Session) -> None:
    """Verify types using mypy."""
    args = session.posargs or (PACKAGE_LOCATION,)
    _install(session, "mypy", "types-requests", "typing-extensions")
    _run(session, "mypy", "--config-file", ".github/linters/.mypy.ini", *args)


@nox.session(python=PYTHON_VERSIONS, tags=["security"])
def bandit(session: nox.Session) -> None:
    """Scan for common security issues with bandit."""
    args = session.posargs or (CODE_LOCATIONS,)
    _install(session, "bandit")
    _run(session, "bandit", *args)


def _install(session: nox.Session, *args: str) -> None:
    if args:
        session.install(*args)


def _run(
    session: nox.Session,
    target: str,
    *args: str,
    silent: bool = SILENT_DEFAULT,
) -> None:
    session.run(target, *args, external=True, silent=silent)


def _run_code_modifier(session: nox.Session, target: str, *args: str) -> None:
    _run(session, target, *args, silent=SILENT_CODE_MODIFIERS)
