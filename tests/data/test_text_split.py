import hashlib
import random

import pytest

import qbestd.data.text_split as text_split
from qbestd.data.text_split import (
    HEADER,
    build_text_split,
    group_hash,
    read_split_manifest,
    split_id,
    write_split_manifest,
)
from qbestd.data.timit_hf import normalize_transcript

SA = "She had your dark suit in greasy wash water all year"


def make_rows(spec):
    """``spec``: (sentence, rows in HF train, rows in HF test) tuples.

    Returns ``(hf_split, row_index, sentence)`` rows and a lookup from
    ``(hf_split, row_index)`` to the sentence.
    """
    counters = {"train": 0, "test": 0}
    rows = []
    for sentence, n_train, n_test in spec:
        for split, count in (("train", n_train), ("test", n_test)):
            for _ in range(count):
                rows.append((split, counters[split], sentence))
                counters[split] += 1
    return rows, {(s, i): text for s, i, text in rows}


def sides(manifest, lookup):
    """Set of normalised texts per side."""
    out = {"train": set(), "test": set()}
    for row in manifest.rows:
        out[row.side].add(" ".join(
            normalize_transcript(lookup[(row.hf_split, row.row_index)])))
    return out


def test_every_group_is_on_one_side_and_texts_are_disjoint():
    rows, lookup = make_rows([
        ("I love tea", 3, 2), ("we love food", 1, 0), ("love is all", 0, 1),
        ("a quiet street", 2, 2), ("the long road", 1, 0),
        ("an old song", 0, 1), (SA, 4, 4)])
    manifest = build_text_split(rows, [("love", 3, 2)])
    texts = sides(manifest, lookup)
    assert texts["train"].isdisjoint(texts["test"])
    assert len(manifest.rows) == len(rows) - 8  # the SA rows are gone
    by_hash = {}
    for row in manifest.rows:
        by_hash.setdefault(row.group_hash, set()).add(row.side)
    assert all(len(found) == 1 for found in by_hash.values())


def test_shuffled_input_gives_a_byte_identical_manifest(tmp_path):
    rows, _ = make_rows([("I love tea", 3, 2), ("we love food", 1, 0),
                         ("love is all", 0, 1), ("a quiet street", 2, 2),
                         ("the long road", 1, 0), ("an old song", 0, 1)])
    shuffled = rows[:]
    random.Random(7).shuffle(shuffled)
    write_split_manifest(tmp_path / "a.tsv",
                         build_text_split(rows, [("love", 3, 2)]))
    write_split_manifest(tmp_path / "b.tsv",
                         build_text_split(shuffled, [("love", 3, 2)]))
    assert (tmp_path / "a.tsv").read_bytes() == \
        (tmp_path / "b.tsv").read_bytes()
    assert split_id(tmp_path / "a.tsv") == split_id(tmp_path / "b.tsv")


def test_a_cost_zero_assignment_is_found_and_ties_go_to_the_smallest_hash():
    # love tokens per group 2, 1, 1, 1: test must hold 2, train 3.
    spec = [("I love tea", 2, 0), ("we love food", 1, 0),
            ("love is all", 1, 0), ("love wins", 1, 0)]
    rows, _ = make_rows(spec)
    manifest = build_text_split(rows, [("love", 3, 2)])
    assert manifest.report["costs"] == {"love": 0}
    assert manifest.report["keyword_tokens"]["love"] == {"train": 3,
                                                          "test": 2}
    hashes = {name: group_hash(" ".join(normalize_transcript(name)))
              for name, _, _ in spec}
    tokens = {"I love tea": 2, "we love food": 1, "love is all": 1,
              "love wins": 1}
    candidates = [
        ("I love tea",), ("we love food", "love is all"),
        ("we love food", "love wins"), ("love is all", "love wins")]
    assert all(sum(tokens[n] for n in c) == 2 for c in candidates)
    expected = min(tuple(sorted(hashes[n] for n in c)) for c in candidates)
    got = tuple(sorted({r.group_hash for r in manifest.rows
                        if r.side == "test"}))
    assert got == expected


def sibling_text(base, anchor):
    """A text ``"<base> n"`` whose group hash is below that of ``anchor``."""
    anchor_hash = group_hash(anchor)
    for number in range(1000):
        text = f"{base} {number}"
        if group_hash(text) < anchor_hash:
            return text
    raise AssertionError("no smaller hash found")


def test_joint_components_solve_what_one_keyword_at_a_time_cannot():
    # "meeting tomorrow" (2 rows) is shared. meeting: Inst 2, Occ 2 is met by
    # either shared group "A" or "B" on test; tomorrow: Inst 1, Occ 2 needs A
    # on test. B is built to have the smaller hash, so deciding meeting first
    # sends B to test and leaves tomorrow at a cost.
    shared = "meeting tomorrow"
    other_meeting = sibling_text("meeting again", shared)
    spec = [(shared, 2, 0), (other_meeting, 2, 0), ("see you tomorrow", 1, 0)]
    rows, _ = make_rows(spec)
    alone = build_text_split(rows, [("meeting", 2, 2)])
    test_alone = {r.group_hash for r in alone.rows if r.side == "test"}
    assert group_hash(other_meeting) in test_alone  # the sequential choice
    joint = build_text_split(rows, [("meeting", 2, 2), ("tomorrow", 1, 2)])
    assert [c["keywords"] for c in joint.report["components"]] == [
        ["meeting", "tomorrow"]]
    assert joint.report["costs"] == {"meeting": 0, "tomorrow": 0}
    test_joint = {r.group_hash for r in joint.rows if r.side == "test"}
    assert group_hash(shared) in test_joint
    assert group_hash(other_meeting) not in test_joint


def test_components_follow_table_order_of_their_first_keyword():
    rows, _ = make_rows([("red love", 1, 0), ("blue cup", 1, 0),
                         ("green hill", 1, 0)])
    keywords = [("blue", 1, 0), ("love", 1, 0), ("red", 0, 1),
                ("hill", 0, 0)]
    report = build_text_split(rows, keywords).report
    assert [c["keywords"] for c in report["components"]] == [
        ["blue"], ["love", "red"], ["hill"]]


def single_quota(monkeypatch):
    monkeypatch.setattr(text_split, "TEST_QUOTA", {"multi": 0, "single": 1})


def test_two_cost_zero_assignments_are_counted_and_tie_break_kept(
        monkeypatch):
    single_quota(monkeypatch)
    rows, _ = make_rows([("red cup", 1, 0), ("red hat", 1, 0)])
    manifest = build_text_split(rows, [("red", 1, 1)])
    [component] = manifest.report["components"]
    assert component == {"keywords": ["red"], "n_groups": 2, "cost": 0,
                         "n_min_assignments": 2}
    test_side = {r.group_hash for r in manifest.rows if r.side == "test"}
    assert test_side == {min(group_hash("red cup"), group_hash("red hat"))}


def test_a_shared_group_component_has_one_count_not_one_per_keyword(
        monkeypatch):
    single_quota(monkeypatch)
    rows, _ = make_rows([("red cup", 1, 0), ("red hat", 1, 0),
                         ("cup mug", 1, 0)])
    keywords = [("red", 1, 1), ("cup", 1, 1)]
    report = build_text_split(rows, keywords).report
    [component] = report["components"]
    assert component["keywords"] == ["red", "cup"]
    assert component["n_groups"] == 3 and component["cost"] == 0
    # A on test with B, C on train; or B, C on test with A on train
    assert component["n_min_assignments"] == 2


def test_a_unique_minimum_counts_one_and_a_nonzero_cost_is_reported(
        monkeypatch):
    single_quota(monkeypatch)
    rows, _ = make_rows([("red cup", 1, 0)])
    [component] = build_text_split(rows, [("red", 3, 3)]).report[
        "components"]
    assert component["n_min_assignments"] == 2  # either side: cost 5 each
    assert component["cost"] == 5
    rows, _ = make_rows([("red cup", 1, 0), ("red hat", 2, 0)])
    [component] = build_text_split(rows, [("red", 2, 1)]).report[
        "components"]
    assert component["cost"] == 0 and component["n_min_assignments"] == 1


def test_quotas_are_met_in_hash_order(monkeypatch):
    monkeypatch.setattr(text_split, "TEST_QUOTA", {"multi": 2, "single": 3})
    spec = ([(f"multi text {i}", 1, 1) for i in range(5)] +
            [(f"single text {i}", 1, 0) for i in range(8)])
    rows, _ = make_rows(spec)
    manifest = build_text_split(rows, [])
    test_hashes = {r.group_hash for r in manifest.rows if r.side == "test"}
    multi = sorted(group_hash(f"multi text {i}") for i in range(5))
    single = sorted(group_hash(f"single text {i}") for i in range(8))
    assert test_hashes == set(multi[:2]) | set(single[:3])
    assert manifest.report["quotas"]["multi"]["added"] == 2


def test_a_quota_exceeded_in_step_2_moves_nothing_and_is_reported(
        monkeypatch):
    monkeypatch.setattr(text_split, "TEST_QUOTA", {"multi": 0, "single": 1})
    spec = [("red cup", 1, 1), ("blue sky", 1, 0), ("green hill", 1, 0)]
    rows, _ = make_rows(spec)
    manifest = build_text_split(rows, [("red", 0, 2)])
    quota = manifest.report["quotas"]["multi"]
    assert quota["exceeded_by"] == 1
    assert {r.side for r in manifest.rows
            if r.group_hash == group_hash("red cup")} == {"test"}


def test_a_stratum_without_enough_groups_reports_the_shortfall(monkeypatch):
    monkeypatch.setattr(text_split, "TEST_QUOTA", {"multi": 0, "single": 5})
    rows, _ = make_rows([("blue sky", 1, 0), ("green hill", 1, 0)])
    manifest = build_text_split(rows, [])
    assert manifest.report["quotas"]["single"]["short_by"] == 3


def test_too_many_free_groups_is_refused():
    spec = [(f"love word{i}", 1, 0) for i in range(17)]
    rows, _ = make_rows(spec)
    with pytest.raises(ValueError, match="too many"):
        build_text_split(rows, [("love", 5, 5)])


def test_manifest_file_roundtrip_has_no_text_and_a_stable_id(tmp_path):
    rows, _ = make_rows([("I love tea", 2, 1), ("a quiet street", 1, 1)])
    manifest = build_text_split(rows, [("love", 2, 1)])
    path = tmp_path / "split.tsv"
    write_split_manifest(path, manifest)
    raw = path.read_bytes()
    assert b"\r" not in raw and b"love" not in raw
    assert raw.decode().splitlines()[0] == "# rule=textdisjoint_q20_v1"
    assert tuple(raw.decode().splitlines()[1].split("\t")) == HEADER
    loaded = read_split_manifest(path)
    assert loaded.rows == manifest.rows
    digest = hashlib.sha256(raw).hexdigest()[:12]
    assert split_id(path) == f"textdisjoint_q20_v1-{digest}"
    assert loaded.side_rows("train", "test") | loaded.side_rows(
        "train", "train") == {0, 1, 2}


def test_bad_header_is_rejected(tmp_path):
    path = tmp_path / "bad.tsv"
    path.write_text("hf_split\trow_index\n")
    with pytest.raises(ValueError):
        read_split_manifest(path)
