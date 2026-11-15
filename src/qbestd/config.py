"""Dataset location configuration.

Priority for each location: environment variable ``QBESTD_<NAME>``, then the
TOML file, then None. Nothing is checked on disk until
``DatasetPaths.require`` is called.

The TOML file is, in order: the ``paths_file`` argument, the file named by
``$QBESTD_PATHS_FILE``, or ``paths.local.toml`` in the repository root (found
from this module's location, so the current directory does not matter). Copy
``paths.local.toml.example`` to create it; it is git-ignored.
"""

import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PATHS_FILE_ENV_VAR = "QBESTD_PATHS_FILE"
DEFAULT_PATHS_FILE = REPO_ROOT / "paths.local.toml"


@dataclass(frozen=True)
class DatasetPaths:
    """Locations of the datasets and scoring tools; a field may be None."""

    timit: Path | None = None
    sws2013: Path | None = None
    quesst2014: Path | None = None
    scoring: Path | None = None

    @classmethod
    def field_names(cls):
        return [field.name for field in fields(cls)]

    @classmethod
    def load(cls, environ=None, paths_file=None):
        """Resolve all locations from env vars and the TOML file.

        Raises:
            ValueError: if an env var is set but empty, or the TOML file
                contains a key that is not a known location.
        """
        environ = os.environ if environ is None else environ
        file_values = _read_paths_file(_choose_paths_file(environ, paths_file))
        unknown = set(file_values) - set(cls.field_names())
        if unknown:
            raise ValueError(f"Unknown keys in paths file: {sorted(unknown)}")
        resolved = {}
        for name in cls.field_names():
            raw = _env_value(environ, name)
            if raw is None:
                raw = file_values.get(name)
            resolved[name] = Path(raw) if raw else None
        return cls(**resolved)

    def require(self, name):
        """Return the path called ``name``, or raise if unset or missing.

        Raises:
            ValueError: if ``name`` is not a known location.
            FileNotFoundError: if the location is unset or does not exist,
                with a hint on how to configure it.
        """
        if name not in self.field_names():
            raise ValueError(
                f"Unknown dataset '{name}'; "
                f"choose one of {self.field_names()}")
        path = getattr(self, name)
        hint = (f"Set QBESTD_{name.upper()} or add it to paths.local.toml "
                f"(see paths.local.toml.example).")
        if path is None:
            raise FileNotFoundError(
                f"No location configured for '{name}'. {hint}")
        if not path.exists():
            raise FileNotFoundError(
                f"Configured path for '{name}' does not exist: {path}. {hint}")
        return path


def _choose_paths_file(environ, paths_file):
    if paths_file is not None:
        return Path(paths_file)
    from_env = environ.get(PATHS_FILE_ENV_VAR)
    return Path(from_env) if from_env else DEFAULT_PATHS_FILE


def _read_paths_file(path):
    if not path.is_file():
        return {}
    with open(path, "rb") as handle:
        return tomllib.load(handle)


def _env_value(environ, name):
    key = f"QBESTD_{name.upper()}"
    if key not in environ:
        return None
    value = environ[key]
    if not value.strip():
        raise ValueError(f"Environment variable {key} is set but empty")
    return value
