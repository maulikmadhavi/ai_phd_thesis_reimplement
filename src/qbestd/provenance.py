"""Run provenance: which commit a run started from, and was the tree clean.

A run records ``git_commit_start``, ``git_commit_end``, ``git_dirty`` and
``allow_dirty``. The tree counts as dirty when ``git status --porcelain``
lists anything under ``src``, ``pixi.toml`` or ``pixi.lock`` (tracked changes
and untracked files alike). A dirty tree refuses to start a run unless
``--allow-dirty`` is passed; docs quote the start commit.
"""

import subprocess

WATCHED_PATHS = ("src", "pixi.toml", "pixi.lock")


class DirtyTreeError(RuntimeError):
    """The working tree has uncommitted changes under the watched paths."""


def _git(args, repo):
    try:
        return subprocess.run(["git", *args], text=True, capture_output=True,
                              check=True, cwd=repo).stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def git_head(repo=None):
    """``git rev-parse HEAD`` of ``repo`` (default: the current directory),
    or ``None`` when it cannot be read."""
    out = _git(["rev-parse", "HEAD"], repo)
    return out.strip() if out is not None else None


def tree_is_dirty(repo=None):
    """True when ``git status --porcelain`` lists a watched path.

    A repository that cannot be read counts as dirty (unknown is not clean).
    """
    out = _git(["status", "--porcelain", "--", *WATCHED_PATHS], repo)
    return out is None or bool(out.strip())


def start_run(allow_dirty=False, repo=None):
    """Provenance of a run that is starting.

    Raises:
        DirtyTreeError: on a dirty tree without ``allow_dirty``.
    """
    dirty = tree_is_dirty(repo)
    if dirty and not allow_dirty:
        raise DirtyTreeError(
            "uncommitted changes under src, pixi.toml or pixi.lock: commit "
            "them first, or pass --allow-dirty (the flag is recorded)")
    return {"git_commit_start": git_head(repo), "git_dirty": dirty,
            "allow_dirty": bool(allow_dirty)}


def finish_run(record, repo=None):
    """``record`` plus ``git_commit_end``."""
    return {**record, "git_commit_end": git_head(repo)}
