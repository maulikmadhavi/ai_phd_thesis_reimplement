from pathlib import Path

import pytest

from qbestd.config import DEFAULT_PATHS_FILE, REPO_ROOT, DatasetPaths


@pytest.fixture
def no_file(tmp_path):
    return tmp_path / "absent.toml"


def test_everything_is_none_by_default(no_file):
    paths = DatasetPaths.load({}, paths_file=no_file)
    assert all(getattr(paths, name) is None for name in paths.field_names())


def test_env_var_sets_location(tmp_path, no_file):
    paths = DatasetPaths.load({"QBESTD_SWS2013": str(tmp_path)}, no_file)
    assert paths.sws2013 == tmp_path


def test_precedence_env_over_file_over_none(tmp_path):
    toml_file = tmp_path / "paths.local.toml"
    toml_file.write_text('timit = "/from/toml"\nscoring = "/scoring/toml"\n')
    paths = DatasetPaths.load({"QBESTD_SCORING": "/scoring/env"}, toml_file)
    assert paths.timit == Path("/from/toml")
    assert paths.scoring == Path("/scoring/env")
    assert paths.sws2013 is None


def test_empty_env_var_raises(no_file):
    with pytest.raises(ValueError, match="QBESTD_TIMIT"):
        DatasetPaths.load({"QBESTD_TIMIT": ""}, no_file)
    with pytest.raises(ValueError):
        DatasetPaths.load({"QBESTD_TIMIT": "   "}, no_file)


def test_unknown_key_in_file_raises(tmp_path):
    toml_file = tmp_path / "paths.toml"
    toml_file.write_text('timitt = "/typo"\n')
    with pytest.raises(ValueError, match="timitt"):
        DatasetPaths.load({}, toml_file)


def test_paths_file_from_env_var(tmp_path):
    toml_file = tmp_path / "elsewhere.toml"
    toml_file.write_text('quesst2014 = "/q14"\n')
    paths = DatasetPaths.load({"QBESTD_PATHS_FILE": str(toml_file)})
    assert paths.quesst2014 == Path("/q14")


def test_default_file_is_found_outside_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert DEFAULT_PATHS_FILE == REPO_ROOT / "paths.local.toml"
    assert DEFAULT_PATHS_FILE.is_absolute()
    assert (REPO_ROOT / "pixi.toml").is_file()  # root resolved from module path


def test_missing_path_errors_only_when_required(tmp_path, no_file):
    paths = DatasetPaths.load({"QBESTD_TIMIT": str(tmp_path / "nope")}, no_file)
    assert paths.timit == tmp_path / "nope"  # no error on access
    with pytest.raises(FileNotFoundError, match="QBESTD_TIMIT"):
        paths.require("timit")


def test_unset_location_gives_clear_error(no_file):
    paths = DatasetPaths.load({}, no_file)
    with pytest.raises(FileNotFoundError, match="No location configured"):
        paths.require("timit")


def test_require_returns_existing_path(tmp_path, no_file):
    paths = DatasetPaths.load({"QBESTD_TIMIT": str(tmp_path)}, no_file)
    assert paths.require("timit") == tmp_path


def test_require_unknown_name_raises_value_error(no_file):
    with pytest.raises(ValueError, match="typo"):
        DatasetPaths.load({}, no_file).require("typo")
