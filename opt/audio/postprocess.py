import numpy as np
import torch
import torchaudio

from opt.logging_setup import setup_logging

logger = setup_logging(__name__)


def apply_noise_gate(audio: np.ndarray, gate_db: float) -> np.ndarray:
    if gate_db is None:
        return audio
    threshold = 10 ** (gate_db / 20)
    gated = np.where(np.abs(audio) < threshold, 0.0, audio)
    logger.debug("Applied noise gate at %.2f dB", gate_db)
    return gated


def high_freq_restore(audio: np.ndarray, sample_rate: int, amount: float) -> np.ndarray:
    if amount <= 0:
        return audio
    tensor = torch.from_numpy(audio.T)
    high = torchaudio.functional.highpass_biquad(tensor, sample_rate, cutoff_freq=4000)
    restored = audio + amount * high.T.numpy()
    logger.debug("Applied high-frequency restore amount=%.2f", amount)
    return restored


def suppress_vocal_band(audio: np.ndarray, sample_rate: int, gain_db: float) -> np.ndarray:
    if gain_db is None or gain_db >= 0:
        return audio
    tensor = torch.from_numpy(audio.T)
    # cascade several cuts across vocal-heavy regions to suppress residual speech
    freqs = (350.0, 700.0, 1200.0, 2500.0, 4000.0)
    per_band_gain = gain_db / len(freqs)
    for freq in freqs:
        tensor = torchaudio.functional.equalizer_biquad(
            tensor, sample_rate=sample_rate, center_freq=freq, gain=per_band_gain, Q=1.1
        )
    logger.debug("Applied vocal-band suppression gain=%.1f dB", gain_db)
    return tensor.T.numpy()
