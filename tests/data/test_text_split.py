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


VARIANT_ROWS = [("we love tea", 3, 0), ("we love the tea", 0, 1),
                ("a quiet street", 1, 0), ("the long road", 1, 0)]


def linked(*texts):
    return tuple(sorted(group_hash(t) for t in texts))


def variant_universe():
    rows, _ = make_rows(VARIANT_ROWS)
    return rows


def test_linked_variants_never_cross_sides_where_v1_would_split_them(
        monkeypatch):
    monkeypatch.setattr(text_split, "TEST_QUOTA", {"multi": 1, "single": 0})
    rows = variant_universe()
    v1 = build_text_split(rows, [])
    split_v1 = {(r.hf_split, r.row_index): r.side for r in v1.rows}
    assert {split_v1[("train", 0)], split_v1[("test", 0)]} == {
        "train", "test"}  # v1 puts the two variants on opposite sides
    link = linked("we love tea", "we love the tea")
    v2 = build_text_split(rows, [], rule=text_split.RULE_V2, links=(link,))
    sides = {r.side for r in v2.rows if r.group_hash == min(link)}
    assert sides == {"test"} and len(
        [r for r in v2.rows if r.group_hash == min(link)]) == 4
    assert v2.rule == "textdisjoint_q20_v2"
    assert v2.report["n_variant_groups"] == 4 and v2.report["n_groups"] == 3


def test_the_unit_key_is_the_smallest_member_hash():
    rows = variant_universe()
    link = linked("we love tea", "we love the tea")
    manifest = build_text_split(rows, [], rule=text_split.RULE_V2,
                                links=(link,))
    keys = {r.group_hash for r in manifest.rows
            if (r.hf_split, r.row_index) in {("train", 0), ("train", 1),
                                            ("train", 2), ("test", 0)}}
    assert keys == {min(link)}


def test_no_links_reproduce_v1_rows_on_a_synthetic_universe():
    rows, _ = make_rows(VARIANT_ROWS + [("see you tomorrow", 2, 1)])
    keywords = [("tomorrow", 2, 1)]
    v1 = build_text_split(rows, keywords)
    v2 = build_text_split(rows, keywords, rule=text_split.RULE_V2, links=())
    assert v2.rows == v1.rows and v2.report == v1.report
    assert v1.rule != v2.rule


def test_v2_manifest_is_identical_under_shuffled_rows_and_links():
    spec = VARIANT_ROWS + [("we run fast", 2, 0), ("we run very fast", 1, 0),
                           ("see you tomorrow", 2, 1)]
    links = [linked("we love tea", "we love the tea"),
             linked("we run fast", "we run very fast")]
    reference = None
    for seed in range(4):
        rows, _ = make_rows(spec)
        random.Random(seed).shuffle(rows)
        random.Random(seed).shuffle(links)
        manifest = build_text_split(rows, [("tomorrow", 2, 1)],
                                    rule=text_split.RULE_V2,
                                    links=tuple(links))
        data = text_split.manifest_bytes(manifest)
        reference = reference or data
        assert data == reference
    assert reference.decode().startswith("# rule=textdisjoint_q20_v2\n")


def test_keyword_counts_sum_over_the_variants_of_a_unit():
    rows, _ = make_rows([("we love tea", 3, 0), ("we like tea", 1, 0)])
    link = linked("we love tea", "we like tea")
    manifest = build_text_split(rows, [("love", 3, 0)],
                                rule=text_split.RULE_V2, links=(link,))
    assert manifest.report["keyword_tokens"]["love"] == {"train": 3,
                                                         "test": 0}
    assert manifest.report["costs"] == {"love": 0}


def test_a_link_naming_an_unknown_hash_raises():
    rows = variant_universe()
    unknown = (group_hash("we love tea"), "f" * 64)
    with pytest.raises(ValueError, match="unknown group hash"):
        build_text_split(rows, [], rule=text_split.RULE_V2, links=(unknown,))


def test_a_link_must_be_a_sorted_pair_of_two_hashes():
    rows = variant_universe()
    link = linked("we love tea", "we love the tea")
    with pytest.raises(ValueError, match="sorted pair"):
        build_text_split(rows, [], rule=text_split.RULE_V2,
                         links=(link[::-1],))
    with pytest.raises(ValueError, match="sorted pair"):
        build_text_split(rows, [], rule=text_split.RULE_V2,
                         links=((link[0], link[0]),))


def test_a_unit_of_more_than_seven_rows_raises():
    rows, _ = make_rows([("one two", 4, 0), ("one too", 4, 0)])
    link = linked("one two", "one too")
    with pytest.raises(ValueError, match="more than 7"):
        build_text_split(rows, [], rule=text_split.RULE_V2, links=(link,))


def test_v2_defaults_to_the_committed_links(monkeypatch):
    rows = variant_universe()
    link = linked("we love tea", "we love the tea")
    monkeypatch.setattr(text_split, "V2_VARIANT_LINKS", (link,))
    manifest = build_text_split(rows, [], rule=text_split.RULE_V2)
    assert manifest.report["n_links"] == 1
    assert build_text_split(rows, []).report["n_links"] == 0
