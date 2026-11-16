import subprocess

import pytest

from qbestd.provenance import (
    DirtyTreeError,
    finish_run,
    git_head,
    start_run,
    tree_is_dirty,
)


def git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                    *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    (tmp_path / "pixi.toml").write_text("[project]\n")
    (tmp_path / "docs.md").write_text("doc\n")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "first")
    return tmp_path


def test_a_clean_tree_starts_and_records_the_commit(repo):
    record = start_run(repo=repo)
    assert record == {"git_commit_start": git_head(repo),
                      "git_dirty": False, "allow_dirty": False}
    assert len(record["git_commit_start"]) == 40


def test_a_dirty_tree_is_refused(repo):
    (repo / "src" / "a.py").write_text("x = 2\n")
    assert tree_is_dirty(repo)
    with pytest.raises(DirtyTreeError, match="--allow-dirty"):
        start_run(repo=repo)


def test_an_untracked_file_under_src_counts_as_dirty(repo):
    (repo / "src" / "new.py").write_text("y = 1\n")
    with pytest.raises(DirtyTreeError):
        start_run(repo=repo)


def test_a_dirty_tree_is_allowed_with_the_flag_and_recorded(repo):
    (repo / "pixi.toml").write_text("[project]\nname = 'x'\n")
    record = start_run(allow_dirty=True, repo=repo)
    assert record["git_dirty"] is True and record["allow_dirty"] is True


def test_changes_outside_the_watched_paths_do_not_count(repo):
    (repo / "docs.md").write_text("changed\n")
    assert not tree_is_dirty(repo)
    assert start_run(repo=repo)["git_dirty"] is False


def test_finish_adds_the_end_commit_even_after_a_new_commit(repo):
    record = start_run(repo=repo)
    (repo / "src" / "a.py").write_text("x = 3\n")
    git(repo, "commit", "-q", "-am", "second")
    done = finish_run(record, repo=repo)
    assert done["git_commit_end"] != done["git_commit_start"]
    assert done["git_commit_start"] == record["git_commit_start"]


def test_an_unreadable_repository_counts_as_dirty(tmp_path):
    assert tree_is_dirty(tmp_path / "missing") is True
    assert git_head(tmp_path / "missing") is None
