from pathlib import Path

import pytest

from qbestd.config import DatasetPaths


def test_env_var_overrides_default(tmp_path):
    paths = DatasetPaths.load({"QBESTD_SWS2013": str(tmp_path)},
                              paths_file=tmp_path / "absent.toml")
    assert paths.sws2013 == tmp_path


def test_defaults_used_when_nothing_set(tmp_path):
    paths = DatasetPaths.load({}, paths_file=tmp_path / "absent.toml")
    assert paths.timit is None
    assert paths.quesst2014.name == "quesst14Database"
    assert paths.sws2013.name == "sws2013Database.tgz"


def test_toml_overrides_default_but_env_wins(tmp_path):
    toml_file = tmp_path / "paths.local.toml"
    toml_file.write_text('timit = "/from/toml"\nscoring = "/scoring/toml"\n')
    paths = DatasetPaths.load({"QBESTD_SCORING": "/scoring/env"}, toml_file)
    assert paths.timit == Path("/from/toml")
    assert paths.scoring == Path("/scoring/env")


def test_missing_path_errors_only_when_required(tmp_path):
    paths = DatasetPaths.load({"QBESTD_TIMIT": str(tmp_path / "nope")},
                              paths_file=tmp_path / "absent.toml")
    assert paths.timit == tmp_path / "nope"  # no error on access
    with pytest.raises(FileNotFoundError, match="QBESTD_TIMIT"):
        paths.require("timit")


def test_unset_location_gives_clear_error(tmp_path):
    paths = DatasetPaths.load({}, paths_file=tmp_path / "absent.toml")
    with pytest.raises(FileNotFoundError, match="No location configured"):
        paths.require("timit")


def test_require_returns_existing_path(tmp_path):
    paths = DatasetPaths.load({"QBESTD_TIMIT": str(tmp_path)},
                              paths_file=tmp_path / "absent.toml")
    assert paths.require("timit") == tmp_path
