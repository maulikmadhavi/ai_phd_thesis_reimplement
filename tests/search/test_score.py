import numpy as np
import pytest

from qbestd.search.score import rank_documents, znorm_scores


def test_hand_worked_example():
    # mean 2, deviations -1, 0, 1, sample std = 1 -> scores 1, 0, -1
    assert np.allclose(znorm_scores([1.0, 2.0, 3.0]), [1.0, 0.0, -1.0])


def test_uses_sample_std_not_population_std():
    scores = znorm_scores([0.0, 2.0])
    assert np.allclose(scores, [1 / np.sqrt(2), -1 / np.sqrt(2)])


def test_scores_have_zero_mean_and_unit_sample_std():
    scores = znorm_scores(np.random.default_rng(0).random(50))
    assert scores.mean() == pytest.approx(0.0, abs=1e-12)
    assert scores.std(ddof=1) == pytest.approx(1.0)


@pytest.mark.parametrize("bad", [[1.0], [], [2.0, 2.0, 2.0],
                                 [1.0, np.nan], [1.0, np.inf]])
def test_degenerate_input_raises(bad):
    with pytest.raises(ValueError):
        znorm_scores(bad)


def test_ranking_by_zscore_equals_ranking_by_distance():
    distances = np.random.default_rng(1).random(30)
    by_distance = rank_documents(distances)
    by_score = np.argsort(-znorm_scores(distances), kind="stable")
    assert np.array_equal(by_distance, by_score)


def test_ranking_is_ascending_and_stable_on_ties():
    order = rank_documents([0.5, 0.1, 0.5, 0.1, 0.3])
    assert order.tolist() == [1, 3, 4, 0, 2]
