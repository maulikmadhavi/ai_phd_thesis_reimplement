"""Query features: from the cut clip (primary) or sliced from the utterance.

* ``clip`` (primary, the cycle 4 and 5 behaviour): cut the query interval
  (aligner word interval padded by 20 ms, clipped to the utterance) out of
  the audio and extract features from that clip alone.
* ``slice`` (sensitivity run, not a thesis-mandated correction): extract
  features on the **whole** utterance and keep frame ``t`` when its centre
  ``t * shift + win / 2`` lies in ``[start, end]``, where ``start`` and
  ``end`` are the padded interval of the query example (the word interval
  plus the pad).

``slice`` differs from ``clip`` in the delta and delta-delta values at the
clip edges (they see the neighbouring frames) **and** in every
utterance-level waveform normalisation: DC removal (and any ``max|x|``
scaling) is computed per utterance, which shifts c0 and hence the whole
cepstral vector.
"""

import numpy as np

from qbestd.eval.timit_queries import cut_clip
from qbestd.features.extract import extract_features

MODES = ("clip", "slice")
EDGE_TOLERANCE_S = 1e-9


def frame_centres(n_frames, config):
    """Centre time in seconds of each frame: ``t * shift + win / 2``."""
    return (np.arange(n_frames) * config.shift_ms
            + config.frame_ms / 2.0) / 1000.0


def select_frames(features, config, start_s, end_s):
    """Frames whose centre lies in ``[start_s, end_s]`` (edges inclusive)."""
    centres = frame_centres(len(features), config)
    keep = ((centres >= start_s - EDGE_TOLERANCE_S)
            & (centres <= end_s + EDGE_TOLERANCE_S))
    return features[keep]


def clip_query_features(audio, sample_rate, example, kind, config):
    """Features of the cut clip alone (primary mode)."""
    clip = cut_clip(audio, sample_rate, example)
    return extract_features(clip, sample_rate, kind, config=config)


def slice_query_features(full_features, example, config):
    """Frames of the whole-utterance ``full_features`` inside the interval."""
    return select_frames(full_features, config, example.start_s,
                         example.end_s)


def query_features_for(mode, row, example, kind, config, full_cache):
    """Features of one query in ``mode``; ``full_cache`` keeps utterances.

    Raises:
        ValueError: for an unknown mode.
    """
    if mode == "clip":
        return clip_query_features(row.audio, row.sample_rate, example, kind,
                                   config)
    if mode == "slice":
        key = (example.hf_split, example.row_index)
        if key not in full_cache:
            full_cache[key] = extract_features(row.audio, row.sample_rate,
                                               kind, config=config)
        return slice_query_features(full_cache[key], example, config)
    raise ValueError(f"unknown query feature mode {mode!r}; use {MODES}")
