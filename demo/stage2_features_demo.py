"""Stage 2 demo: acoustic features (MFCC, PLP, MFCC-TMP) with VTLN warping.

Usage:  pixi run -e demo demo-stage2
Upload or record audio, pick a feature type and a VTLN warp factor (1.0 = no
warp), then press Run. The page shows the unwarped and warped mel filterbank,
a heatmap of the features (static, delta and acceleration blocks) and the
mean and standard deviation of every dimension. Features are extracted at
8 kHz; all processing comes from `qbestd`.
"""

import gradio as gr
import numpy as np
from matplotlib.figure import Figure

from qbestd.audio.io import load_audio
from qbestd.audio.spectrum import fft_bin_frequencies
from qbestd.features.extract import FEATURE_KINDS, extract_features
from qbestd.features.filterbank import mel_filterbank
from qbestd.features.mfcc import MfccConfig
from qbestd.features.mfcc_tmp import MfccTmpConfig
from qbestd.features.plp import PlpConfig

SAMPLE_RATE = 8000
N_FFT = 256
LIFTER_ON = 22


def build_config(kind, n_filters, high_hz, include_c0, use_lifter):
    """Config for ``kind`` from the demo controls (PLP ignores high_hz/c0)."""
    lifter = LIFTER_ON if use_lifter else 0
    if kind == "plp":
        return PlpConfig(sample_rate=SAMPLE_RATE, n_filters=int(n_filters),
                         lifter_length=lifter)
    config_class = MfccConfig if kind == "mfcc" else MfccTmpConfig
    return config_class(sample_rate=SAMPLE_RATE, n_filters=int(n_filters),
                        high_hz=float(high_hz), include_c0=include_c0,
                        lifter_length=lifter)


def plot_filterbanks(n_filters, high_hz, warp_factor):
    figure = Figure(figsize=(9, 3))
    axes = figure.subplots(1, 2, sharey=True)
    frequencies = fft_bin_frequencies(N_FFT, SAMPLE_RATE)
    for axis, alpha, title in zip(axes, (1.0, warp_factor),
                                  ("Unwarped (alpha = 1.0)",
                                   f"Warped (alpha = {warp_factor:.2f})")):
        bank = mel_filterbank(int(n_filters), N_FFT, SAMPLE_RATE, 0.0,
                              float(high_hz), alpha)
        axis.plot(frequencies, bank.T, linewidth=0.8)
        axis.set(xlabel="frequency (Hz)", title=title)
    axes[0].set_ylabel("weight")
    figure.tight_layout()
    return figure


def plot_feature_heatmap(features, shift_ms=10.0):
    figure = Figure(figsize=(9, 4))
    axis = figure.subplots()
    image = axis.imshow(features.T, origin="lower", aspect="auto",
                        extent=[0, len(features) * shift_ms / 1000.0,
                                0, features.shape[1]])
    axis.set(xlabel="time (s)", ylabel="feature dimension",
             title="Features (static | delta | acceleration blocks)")
    figure.colorbar(image, ax=axis)
    figure.tight_layout()
    return figure


def describe_dimensions(features):
    """Rows of [dimension, mean, std] for the Dataframe output."""
    return [[index, round(float(mean), 4), round(float(std), 4)]
            for index, (mean, std) in enumerate(
                zip(features.mean(axis=0), features.std(axis=0)))]


def run_features(audio_path, kind, warp_factor, n_filters, high_hz,
                 include_c0, use_lifter):
    """Extract features and return filterbank plot, heatmap and statistics."""
    if audio_path is None:
        raise gr.Error("Please upload or record some audio first.")
    samples, source_rate = load_audio(audio_path)
    config = build_config(kind, n_filters, high_hz, include_c0, use_lifter)
    try:
        features = extract_features(samples, source_rate, kind, warp_factor,
                                    config)
    except ValueError as error:
        raise gr.Error(str(error)) from error
    if len(features) == 0:
        raise gr.Error("Audio is shorter than one frame; use a longer clip.")
    return (plot_filterbanks(n_filters, high_hz, warp_factor),
            plot_feature_heatmap(features), describe_dimensions(features))


def build_demo():
    with gr.Blocks(title="Stage 2: acoustic features") as demo:
        gr.Markdown(__doc__)
        audio = gr.Audio(sources=["upload", "microphone"], type="filepath",
                         label="Input audio")
        with gr.Row():
            kind = gr.Dropdown(list(FEATURE_KINDS), value="mfcc",
                               label="feature type")
            warp = gr.Slider(0.88, 1.12, value=1.0, step=0.02,
                             label="VTLN warp factor")
        with gr.Row():
            n_filters = gr.Slider(14, 40, value=26, step=1, label="n_filters")
            high_hz = gr.Slider(1000, 4000, value=4000, step=100,
                                label="high_hz (MFCC / MFCC-TMP)")
        with gr.Row():
            include_c0 = gr.Checkbox(
                True, label="include c0 (MFCC / MFCC-TMP)")
            use_lifter = gr.Checkbox(False, label="HTK lifter (L = 22)")
        run_button = gr.Button("Run")
        filterbank_plot = gr.Plot(label="Mel filterbank")
        heatmap_plot = gr.Plot(label="Features")
        table = gr.Dataframe(headers=["dimension", "mean", "std"],
                             label="Per-dimension statistics")
        run_button.click(
            run_features,
            [audio, kind, warp, n_filters, high_hz, include_c0, use_lifter],
            [filterbank_plot, heatmap_plot, table])
    return demo


if __name__ == "__main__":
    build_demo().launch()
