"""Stage 1 demo: audio front end (resample, pre-emphasis, framing, spectrum).

Usage:  pixi run -e demo demo-stage1
Upload or record audio, adjust the sliders, and press Run. The page shows the
waveform, the log power spectrogram, the short-time and Teager energy per
frame, and the number of frames produced. All processing comes from `qbestd`.
"""

import gradio as gr
import numpy as np
from matplotlib.figure import Figure

from qbestd.audio.energy import frame_teager_energy, log_energy
from qbestd.audio.io import load_audio
from qbestd.audio.pipeline import AudioFrontEndConfig, prepare_frames
from qbestd.audio.resample import resample_audio
from qbestd.audio.spectrum import fft_bin_frequencies, power_spectrum

SAMPLE_RATES = [8000, 16000]
WINDOWS = ["hamming", "hann", "rectangular"]
LOG_POWER_FLOOR = 1e-10


def plot_waveform(samples, sample_rate):
    figure = Figure(figsize=(8, 2.5))
    axes = figure.subplots()
    axes.plot(np.arange(len(samples)) / sample_rate, samples, linewidth=0.6)
    axes.set(xlabel="time (s)", ylabel="amplitude", title="Waveform")
    figure.tight_layout()
    return figure


def plot_spectrogram(frames, config, sample_rate, shift_ms):
    power = power_spectrum(frames, config.n_fft)
    n_fft = (power.shape[1] - 1) * 2
    figure = Figure(figsize=(8, 3))
    axes = figure.subplots()
    log_power = np.log10(np.maximum(power, LOG_POWER_FLOOR)).T
    duration = len(frames) * shift_ms / 1000.0
    axes.imshow(log_power, origin="lower", aspect="auto",
                extent=[0, duration, 0,
                        fft_bin_frequencies(n_fft, sample_rate)[-1]])
    axes.set(xlabel="time (s)", ylabel="frequency (Hz)",
             title="Log power spectrogram")
    figure.tight_layout()
    return figure


def plot_energy_curves(frames, shift_ms):
    figure = Figure(figsize=(8, 4))
    energy_axes, teager_axes = figure.subplots(2, 1, sharex=True)
    times = np.arange(len(frames)) * shift_ms / 1000.0
    energy_axes.plot(times, log_energy(frames))
    energy_axes.set(ylabel="log energy", title="Short-time energy per frame")
    teager_axes.plot(times, frame_teager_energy(frames))
    teager_axes.axhline(0.0, color="gray", linewidth=0.5)
    teager_axes.set(xlabel="time (s)", ylabel="mean TEO (signed)",
                    title="Teager energy per frame (can be negative)")
    figure.tight_layout()
    return figure


def run_front_end(audio_path, frame_ms, shift_ms, preemphasis, window,
                  target_rate):
    """Run the Stage 1 pipeline and return plots plus a frame-count message."""
    if audio_path is None:
        raise gr.Error("Please upload or record some audio first.")
    samples, source_rate = load_audio(audio_path)
    config = AudioFrontEndConfig(
        sample_rate=int(target_rate), frame_ms=frame_ms, shift_ms=shift_ms,
        preemphasis=preemphasis, window=window)
    frames = prepare_frames(samples, source_rate, config)
    if len(frames) == 0:
        raise gr.Error("Audio is shorter than one frame; use a longer clip.")
    resampled = resample_audio(samples, source_rate, config.sample_rate)
    summary = (f"{len(frames)} frames of {frames.shape[1]} samples "
               f"at {config.sample_rate} Hz (source {source_rate} Hz)")
    return (plot_waveform(resampled, config.sample_rate),
            plot_spectrogram(frames, config, config.sample_rate, shift_ms),
            plot_energy_curves(frames, shift_ms), summary)


def build_demo():
    with gr.Blocks(title="Stage 1: audio front end") as demo:
        gr.Markdown(__doc__)
        audio = gr.Audio(sources=["upload", "microphone"], type="filepath",
                         label="Input audio")
        with gr.Row():
            frame_ms = gr.Slider(10, 50, value=25, step=1, label="frame_ms")
            shift_ms = gr.Slider(5, 25, value=10, step=1, label="shift_ms")
            preemphasis = gr.Slider(0.0, 1.0, value=0.97, step=0.01,
                                    label="pre-emphasis")
        with gr.Row():
            window = gr.Dropdown(WINDOWS, value="hamming", label="window")
            target_rate = gr.Dropdown(SAMPLE_RATES, value=8000,
                                      label="target sample rate")
        run_button = gr.Button("Run")
        waveform_plot = gr.Plot(label="Waveform")
        spectrogram_plot = gr.Plot(label="Spectrogram")
        energy_plot = gr.Plot(label="Energy")
        summary = gr.Textbox(label="Frame count")
        run_button.click(
            run_front_end,
            [audio, frame_ms, shift_ms, preemphasis, window, target_rate],
            [waveform_plot, spectrogram_plot, energy_plot, summary])
    return demo


if __name__ == "__main__":
    build_demo().launch()
