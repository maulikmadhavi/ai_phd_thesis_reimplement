import numpy as np

from qbestd.eval.post_hoc import COMPARISONS, excludes_zero, read_per_query


def test_comparisons_name_both_runs_for_both_features_and_norms():
    assert len(COMPARISONS) == 10
    names = [c for _, _, _, c in COMPARISONS]
    assert "vtln_mfcc_htk_described_4k_pn_gmm64" in names
    assert "cell_query_inherit_plp_4k" in names
    # query_inherit is compared only for the un-normalised rows
    inherit = [c for c in COMPARISONS if "query_inherit" in c[0]]
    assert len(inherit) == 2 and all("pn" not in c[0] for c in inherit)


def test_excludes_zero_reads_both_metrics():
    result = {"instance_average": {
        "p_at_n": {"low": 0.5, "high": 2.0},
        "map": {"low": -1.0, "high": 1.0}}}
    assert excludes_zero(result, "instance_average") == [True, False]


def test_read_per_query_types(tmp_path):
    path = tmp_path / "per_query.tsv"
    path.write_text("keyword\thf_split\trow_index\tword_index\tn_relevant\t"
                    "p_at_n\tap\tnonmatches\n"
                    "artists\ttrain\t366\t2\t7\t42.8571\t0.2909\t0\n",
                    encoding="utf-8")
    (row,) = read_per_query(path)
    assert row["row_index"] == 366 and row["word_index"] == 2
    assert np.isclose(row["ap"], 0.2909)
