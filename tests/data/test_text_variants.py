import pytest

from qbestd.data.text_variants import (
    MAX_UNIT_ROWS,
    V2_VARIANT_LINKS,
    VariantCandidate,
    cross_side_candidates,
    find_variant_candidates,
    one_edit,
)


def group(text, n_rows):
    return {"tokens": text.split(), "rows": [("train", i)
                                             for i in range(n_rows)]}


@pytest.mark.parametrize("first, second, expected", [
    ("a b c", "a x c", ("substitution", "b/x")),
    ("a b c", "a b c d", ("insertion", "d")),
    ("a b c", "a x b c", ("insertion", "x")),
    ("x a b c", "a b c", ("deletion", "x")),
    ("a b c", "a c", ("deletion", "b")),
    ("a b c", "a b", ("deletion", "c")),
    ("a b c", "a b c", None),            # equal
    ("a b c", "a x y", None),            # two substitutions
    ("a b c", "a c b", None),            # a swap
    ("a b c", "a b c d e", None),        # two insertions
    ("a b c", "x b c d", None),          # an insertion and a substitution
    ("a", "", ("deletion", "a")),
])
def test_one_edit_detects_exactly_one_token_difference(first, second,
                                                       expected):
    assert one_edit(first.split(), second.split()) == expected


def test_finder_detects_substitution_insertion_and_deletion():
    groups = {"h1": group("we love red tea", 6),
              "h2": group("we love blue tea", 1),
              "h3": group("a long road home", 5),
              "h4": group("a long road", 1),
              "h5": group("one two three", 3),
              "h6": group("one two three four", 2)}
    found = find_variant_candidates(groups)
    assert found == [
        VariantCandidate("h1", "h2", "substitution", "red/blue", 6, 1),
        VariantCandidate("h3", "h4", "deletion", "home", 5, 1),
        VariantCandidate("h5", "h6", "insertion", "four", 3, 2)]


def test_finder_reports_insertion_relative_to_the_smaller_hash():
    groups = {"h2": group("a b c", 1), "h1": group("a b", 2)}
    [found] = find_variant_candidates(groups)
    assert (found.hash_a, found.hash_b, found.edit) == ("h1", "h2",
                                                        "insertion")


def test_finder_rejects_two_token_edits():
    groups = {"h1": group("one two three four", 4),
              "h2": group("one 2 3 four", 2),
              "h3": group("one three", 2),
              "h4": group("one two three four five six", 2)}
    assert find_variant_candidates(groups) == []


def test_finder_needs_at_least_one_multi_read_group():
    groups = {"h1": group("a b c", 1), "h2": group("a x c", 1)}
    assert find_variant_candidates(groups) == []
    groups["h2"] = group("a x c", 2)
    assert len(find_variant_candidates(groups)) == 1


def test_finder_rejects_combined_row_counts_over_the_limit():
    assert MAX_UNIT_ROWS == 7
    groups = {"h1": group("a b c", 6), "h2": group("a x c", 1)}
    assert len(find_variant_candidates(groups)) == 1  # exactly 7
    groups["h2"] = group("a x c", 2)
    assert find_variant_candidates(groups) == []
    assert len(find_variant_candidates(groups, max_rows=8)) == 1


def test_finder_filters_can_be_lifted_to_count_what_they_exclude():
    groups = {"h1": group("a b c", 1), "h2": group("a x c", 1)}
    assert find_variant_candidates(groups) == []
    assert len(find_variant_candidates(groups, require_multi=False)) == 1


def test_finder_does_not_pair_a_group_with_itself_or_repeat_pairs():
    groups = {"h1": group("a b c", 3), "h2": group("a b", 2),
              "h3": group("b c", 2)}
    found = find_variant_candidates(groups)
    assert [(c.hash_a, c.hash_b) for c in found] == [("h1", "h2"),
                                                    ("h1", "h3")]


def test_cross_side_candidates_lists_pairs_on_opposite_sides():
    groups = {"h1": group("a b c", 3), "h2": group("a x c", 2),
              "h3": group("p q r", 3), "h4": group("p y r", 2)}
    side = {"h1": "train", "h2": "test", "h3": "test", "h4": "test"}
    found = cross_side_candidates(groups, side)
    assert [(c.hash_a, c.hash_b) for c in found] == [("h1", "h2")]


def test_committed_links_are_sorted_distinct_pairs():
    assert list(V2_VARIANT_LINKS) == sorted(V2_VARIANT_LINKS)
    assert len(set(V2_VARIANT_LINKS)) == len(V2_VARIANT_LINKS)
    for first, second in V2_VARIANT_LINKS:
        assert first < second
        assert len(first) == len(second) == 64


def test_a_group_with_two_partners_gives_both_pairs_in_a_fixed_order():
    groups = {"h3": group("a x c d", 2), "h1": group("a b c d", 4),
              "h2": group("a b c", 1)}
    found = find_variant_candidates(groups)
    assert [(c.hash_a, c.hash_b) for c in found] == [("h1", "h2"),
                                                    ("h1", "h3")]
    assert [(c.hash_a, c.hash_b) for c in find_variant_candidates(
        dict(reversed(list(groups.items()))))] == [("h1", "h2"),
                                                  ("h1", "h3")]
