import pytest

from qbestd.eval.bootstrap import cluster_bootstrap, paired_keyword_bootstrap


def item(keyword, row, p, ap, word=0):
    return {"keyword": keyword, "row_index": row, "word_index": word,
            "p_at_n": p, "ap": ap}


THREE = [item("a", 1, 100.0, 1.0), item("a", 2, 100.0, 1.0),
         item("b", 3, 0.0, 0.0), item("c", 4, 50.0, 0.5)]


def test_estimates_are_the_two_averages():
    result = cluster_bootstrap(THREE, n_boot=200)
    assert result["n_keywords"] == 3 and result["n_instances"] == 4
    assert result["instance_average"]["p_at_n"]["estimate"] == 62.5
    assert result["keyword_average"]["p_at_n"]["estimate"] == 50.0
    assert result["instance_average"]["map"]["estimate"] == 62.5
    assert result["keyword_average"]["map"]["estimate"] == 50.0


def test_two_keywords_give_the_known_percentile_interval():
    # keyword means 0 and 100: draws give 0, 50 or 100 with p .25/.5/.25
    two = [item("x", 1, 0.0, 0.0), item("y", 2, 100.0, 1.0)]
    result = cluster_bootstrap(two, n_boot=4000)
    box = result["keyword_average"]["p_at_n"]
    assert (box["low"], box["high"]) == (0.0, 100.0)
    assert box["estimate"] == 50.0


def test_instances_of_a_keyword_are_resampled_together():
    # one keyword with 3 instances and another with 1: an instance-level
    # bootstrap could draw 0 of the 3, a keyword-level one never gives a
    # mean outside the two keyword means.
    data = [item("a", i, 100.0, 1.0) for i in range(3)]
    data.append(item("b", 9, 0.0, 0.0))
    box = cluster_bootstrap(data, n_boot=2000)["instance_average"]["p_at_n"]
    assert box["low"] == 0.0 and box["high"] == 100.0


def test_fixed_seed_gives_a_fixed_result_and_other_seed_may_differ():
    first = cluster_bootstrap(THREE, n_boot=500, seed=3)
    assert first == cluster_bootstrap(THREE, n_boot=500, seed=3)


def test_identical_runs_have_a_zero_paired_interval():
    result = paired_keyword_bootstrap(THREE, THREE, n_boot=300)
    for average in ("instance_average", "keyword_average"):
        for metric in ("p_at_n", "map"):
            box = result[average][metric]
            assert (box["estimate"], box["low"], box["high"]) == (0, 0, 0)


def test_paired_estimate_is_the_mean_difference():
    better = [item("a", 1, 100.0, 1.0), item("a", 2, 100.0, 1.0),
              item("b", 3, 100.0, 1.0), item("c", 4, 50.0, 0.5)]
    result = paired_keyword_bootstrap(THREE, better, n_boot=300)
    assert result["keyword_average"]["p_at_n"]["estimate"] == \
        pytest.approx(100.0 / 3)
    assert result["instance_average"]["p_at_n"]["estimate"] == 25.0


def test_paired_requires_identical_keywords_and_instances():
    with pytest.raises(ValueError):
        paired_keyword_bootstrap(THREE, THREE[:3])
    moved = THREE[:3] + [item("c", 99, 50.0, 0.5)]
    with pytest.raises(ValueError):
        paired_keyword_bootstrap(THREE, moved)


def test_empty_input_raises():
    with pytest.raises(ValueError):
        cluster_bootstrap([])
