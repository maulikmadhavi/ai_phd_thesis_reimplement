"""Dataset location configuration.

Priority for each location: environment variable ``QBESTD_<NAME>``, then the
git-ignored ``paths.local.toml``, then the built-in default. Nothing is
checked on disk until ``DatasetPaths.require`` is called.
"""

import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

DEFAULT_PATHS_FILE = Path("paths.local.toml")

_DEFAULTS = {
    # TIMIT comes from the Hugging Face dataset Siyong/speech_timit; no local default.
    "timit": None,
    "sws2013": r"D:\Storage\research_data\speech_qbe-std\sws2013Database.tgz",
    "quesst2014": (r"D:\Storage\research_code_qbe_std\hquest\data"
                   r"\quesst14Database\quesst14Database"),
    "scoring": (r"D:\Storage\research_data\speech_qbe-std"
                r"\scoring_atwv_sws2013_full.tgz"),
}


@dataclass(frozen=True)
class DatasetPaths:
    """Locations of the datasets and scoring tools; a field may be None."""

    timit: Path | None = None
    sws2013: Path | None = None
    quesst2014: Path | None = None
    scoring: Path | None = None

    @classmethod
    def load(cls, environ=None, paths_file=DEFAULT_PATHS_FILE):
        """Resolve all locations from env vars, the TOML file and defaults."""
        environ = os.environ if environ is None else environ
        file_values = {}
        if Path(paths_file).is_file():
            with open(paths_file, "rb") as handle:
                file_values = tomllib.load(handle)
        resolved = {}
        for field in fields(cls):
            raw = (environ.get(f"QBESTD_{field.name.upper()}")
                   or file_values.get(field.name)
                   or _DEFAULTS[field.name])
            resolved[field.name] = Path(raw) if raw else None
        return cls(**resolved)

    def require(self, name):
        """Return the path called ``name``, or raise if unset or missing.

        Raises:
            FileNotFoundError: with a hint on how to configure the location.
        """
        path = getattr(self, name)
        if path is None:
            raise FileNotFoundError(
                f"No location configured for '{name}'. Set "
                f"QBESTD_{name.upper()} or add it to {DEFAULT_PATHS_FILE}.")
        if not path.exists():
            raise FileNotFoundError(
                f"Configured path for '{name}' does not exist: {path}. "
                f"Set QBESTD_{name.upper()} or edit {DEFAULT_PATHS_FILE}.")
        return path
