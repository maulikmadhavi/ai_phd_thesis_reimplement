"""Query features: from the cut clip (primary) or sliced from the utterance.

* ``clip`` (primary, the cycle 4 and 5 behaviour): cut the query interval
  (aligner word interval padded by 20 ms, clipped to the utterance) out of
  the audio and extract features from that clip alone.
* ``clip_lm`` (level matched, cycle 10, D7 b): the source utterance is
  normalised as the document path normalises it (peak, then mean removal),
  the clip is cut from that, and its features are extracted without any
  further normalisation. Only for profiles that normalise.
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

from dataclasses import replace

import numpy as np

from qbestd.audio.preprocess import remove_dc_offset
from qbestd.eval.timit_queries import cut_clip
from qbestd.features.extract import extract_features
from qbestd.features.frontend import scale_waveform

MODES = ("clip", "slice", "clip_lm")
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


def level_matched_config(config):
    """The extraction config of a ``clip_lm`` query: normalisation is done on
    the utterance, so the clip is extracted with it switched off.

    Raises:
        ValueError: if the profile does not both remove the mean and peak
            normalise (``clip_lm`` is defined for those profiles only).
    """
    if not (config.remove_dc and config.normalize_peak):
        raise ValueError("clip_lm needs a profile with remove_dc and "
                         "normalize_peak both true")
    return replace(config, remove_dc=False, normalize_peak=False)


def level_matched_clip(audio, sample_rate, example, config):
    """The query clip cut from the normalised utterance: peak division, then
    mean removal over the whole utterance, as the document path does it. The
    PCM scale is applied later, by the extraction."""
    scaled = scale_waveform(audio, normalize_peak=True, pcm_scale=1.0)
    normalised = remove_dc_offset(scaled) if config.remove_dc else scaled
    return cut_clip(normalised, sample_rate, example)


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
    if mode == "clip_lm":
        lm_config = level_matched_config(config)
        clip = level_matched_clip(row.audio, row.sample_rate, example, config)
        return extract_features(clip, row.sample_rate, kind, config=lm_config)
    raise ValueError(f"unknown query feature mode {mode!r}; use {MODES}")
