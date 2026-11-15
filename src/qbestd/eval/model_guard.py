"""Refuse to score with a GMM built for other features or another split."""


class ModelMismatchError(ValueError):
    """The model was trained on other features, profile or split."""


def check_model(info, kind, profile, split_id, fingerprint):
    """Raise :class:`ModelMismatchError` unless ``info`` (the model metadata
    from ``load_gmm``) matches the request.

    ``fingerprint`` is ``feature_fingerprint(kind, profile, exclude_sa=True)``
    under the current code. It does not cover which rows were used, which is
    why ``split_id`` is compared as well. A model without these fields (an
    older one) is rejected.
    """
    expected = {"kind": kind, "profile": profile, "split_id": split_id,
                "feature_fingerprint": fingerprint}
    for field, wanted in expected.items():
        if info.get(field) != wanted:
            raise ModelMismatchError(
                f"model {field} is {info.get(field)!r}, expected "
                f"{wanted!r}; retrain with `pixi run train-gmm`")
