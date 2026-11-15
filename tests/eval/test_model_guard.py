import pytest

from qbestd.eval.model_guard import ModelMismatchError, check_model

INFO = {"kind": "mfcc", "profile": "timit_matlab", "split_id": "hf-abc-nonsa",
        "feature_fingerprint": "f" * 64}


def check(info=INFO, **changes):
    request = {"kind": "mfcc", "profile": "timit_matlab",
               "split_id": "hf-abc-nonsa", "fingerprint": "f" * 64}
    check_model(info, **{**request, **changes})


def test_matching_model_passes():
    check()


@pytest.mark.parametrize("change, field", [
    ({"kind": "plp"}, "kind"), ({"profile": "other"}, "profile"),
    ({"split_id": "textdisjoint_q20_v1-1"}, "split_id"),
    ({"fingerprint": "0" * 64}, "feature_fingerprint")])
def test_each_mismatched_field_is_rejected(change, field):
    with pytest.raises(ModelMismatchError, match=field):
        check(**change)


@pytest.mark.parametrize("missing", list(INFO))
def test_model_without_a_field_is_rejected(missing):
    info = {k: v for k, v in INFO.items() if k != missing}
    with pytest.raises(ModelMismatchError, match=missing):
        check(info)
