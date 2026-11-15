"""Stage 3 demo: Gaussian posteriorgram of a diagonal GMM.

Usage:  pixi run -e demo demo-stage3
Upload or record audio and pick a feature type. If a trained model matching
that feature type exists in ``outputs/models/*.npz`` you can select it;
otherwise (or when you choose "train on this clip") a small GMM is trained on
the clip itself with the number of components from the slider (rounded down to
a power of two, 4 to 64; the clip needs at least that many frames). The page
shows the posteriorgram (frames x components), the most likely component per
frame, the mean log-likelihood per frame and, when a GMM was trained here,
its EM log-likelihood curve. Features use the ``timit_matlab`` profile
(16 kHz, 39 dimensions). All processing comes from ``qbestd``.
"""

from pathlib import Path

import gradio as gr
import numpy as np
from matplotlib.figure import Figure

from qbestd.audio.io import load_audio
from qbestd.features.extract import FEATURE_KINDS, extract_features
from qbestd.features.profiles import get_profile
from qbestd.ml.gmm import (
    frame_log_likelihoods,
    load_gmm,
    train_gmm_detailed,
)
from qbestd.ml.posteriorgram import gaussian_posteriorgram

PROFILE = "timit_matlab"
MODELS_DIR = Path("outputs/models")
TRAIN_ON_CLIP = "train on this clip"
SHIFT_S = 0.010


def list_models(kind):
    """Model files in ``outputs/models`` whose metadata matches ``kind``."""
    found = []
    for path in sorted(MODELS_DIR.glob("*.npz")):
        try:
            _, meta = load_gmm(path)
        except (OSError, ValueError, KeyError):
            continue
        if meta.get("kind") == kind and meta.get("profile") == PROFILE:
            found.append(path.name)
    return found


def model_choices(kind):
    """Dropdown update: matching models plus the train-on-clip option."""
    choices = [TRAIN_ON_CLIP] + list_models(kind)
    return gr.update(choices=choices, value=choices[-1])


def round_to_power_of_two(value):
    """Largest power of two not above ``value`` (at least 1)."""
    return 1 << max(int(value).bit_length() - 1, 0)


def obtain_gmm(features, model_name, n_components):
    """(gmm, EM history or None, description) for the chosen model option."""
    if model_name != TRAIN_ON_CLIP:
        gmm, meta = load_gmm(MODELS_DIR / model_name)
        if gmm.dim != features.shape[1]:
            raise gr.Error(f"{model_name} has {gmm.dim} dims, features have "
                           f"{features.shape[1]}.")
        return gmm, None, f"{model_name} ({gmm.n_components} components)"
    k = round_to_power_of_two(n_components)
    if len(features) < k:
        raise gr.Error(f"Clip has {len(features)} frames, fewer than the "
                       f"{k} components; use a longer clip or fewer.")
    result = train_gmm_detailed(features, k, n_iter=10)
    return (result.gmm, result.log_likelihood_history,
            f"trained on this clip ({k} components, 10 EM iterations)")


def plot_posteriorgram(grid):
    figure = Figure(figsize=(9, 3.5))
    axis = figure.subplots()
    image = axis.imshow(grid.T, origin="lower", aspect="auto",
                        extent=[0, len(grid) * SHIFT_S, 0, grid.shape[1]])
    axis.set(xlabel="time (s)", ylabel="component",
             title="Gaussian posteriorgram P(C_k | o_t)")
    figure.colorbar(image, ax=axis)
    figure.tight_layout()
    return figure


def plot_top_component(grid):
    figure = Figure(figsize=(9, 2.5))
    axis = figure.subplots()
    times = np.arange(len(grid)) * SHIFT_S
    axis.step(times, np.argmax(grid, axis=1), where="post")
    axis.set(xlabel="time (s)", ylabel="top component",
             title="Most likely component per frame")
    figure.tight_layout()
    return figure


def plot_frame_log_likelihood(values):
    figure = Figure(figsize=(9, 2.5))
    axis = figure.subplots()
    axis.plot(np.arange(len(values)) * SHIFT_S, values, linewidth=0.8)
    axis.set(xlabel="time (s)", ylabel="log-likelihood",
             title=f"Per-frame log-likelihood (mean {values.mean():.2f})")
    figure.tight_layout()
    return figure


def plot_em_curve(history):
    """EM curve figure, or None when a saved model was used."""
    if history is None:
        return None
    figure = Figure(figsize=(5, 3))
    axis = figure.subplots()
    axis.plot(range(len(history)), history, marker="o")
    axis.set(xlabel="EM iteration (0 = LBG initialisation)",
             ylabel="mean frame log-likelihood", title="EM convergence")
    figure.tight_layout()
    return figure


def run_gmm(audio_path, kind, model_name, n_components):
    """Extract features, get a GMM and return the four plots plus a note."""
    if audio_path is None:
        raise gr.Error("Please upload or record some audio first.")
    samples, rate = load_audio(audio_path)
    features = extract_features(samples, rate, kind,
                                config=get_profile(PROFILE, kind))
    if len(features) == 0:
        raise gr.Error("Audio is shorter than one frame; use a longer clip.")
    gmm, history, description = obtain_gmm(features, model_name, n_components)
    grid = gaussian_posteriorgram(gmm, features)
    log_likelihood = frame_log_likelihoods(gmm, features)
    note = (f"{len(features)} frames x {features.shape[1]} dims; GMM: "
            f"{description}; mean frame log-likelihood "
            f"{log_likelihood.mean():.3f}")
    return (plot_posteriorgram(grid), plot_top_component(grid),
            plot_frame_log_likelihood(log_likelihood), plot_em_curve(history),
            note)


def build_demo():
    with gr.Blocks(title="Stage 3: GMM posteriorgram") as demo:
        gr.Markdown(__doc__)
        audio = gr.Audio(sources=["upload", "microphone"], type="filepath",
                         label="Input audio")
        with gr.Row():
            kind = gr.Dropdown(list(FEATURE_KINDS), value="mfcc",
                               label="feature type")
            model = gr.Dropdown([TRAIN_ON_CLIP] + list_models("mfcc"),
                                value=(list_models("mfcc") or
                                       [TRAIN_ON_CLIP])[-1], label="GMM")
            components = gr.Slider(4, 64, value=16, step=1,
                                   label="components (train on clip)")
        kind.change(model_choices, kind, model)
        run_button = gr.Button("Run")
        note = gr.Markdown()
        posteriorgram = gr.Plot(label="Posteriorgram")
        top = gr.Plot(label="Top component")
        likelihood = gr.Plot(label="Per-frame log-likelihood")
        curve = gr.Plot(label="EM log-likelihood (when trained here)")
        run_button.click(run_gmm, [audio, kind, model, components],
                         [posteriorgram, top, likelihood, curve, note])
    return demo


if __name__ == "__main__":
    build_demo().launch()
