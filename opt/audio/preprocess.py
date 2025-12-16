from pathlib import Path
from typing import Tuple

import numpy as np
import soundfile as sf
import torch
import torchaudio

from opt.logging_setup import setup_logging

logger = setup_logging(__name__)

AudioTuple = Tuple[np.ndarray, int]


def load_audio(path: Path, target_sr: int = 48000) -> AudioTuple:
    data, sr = sf.read(path)
    if data.ndim == 1:
        data = data[:, None]
    logger.debug("Loaded audio %s with shape %s @ %s Hz", path, data.shape, sr)
    if sr != target_sr:
        tensor = torch.from_numpy(data.T)
        resampled = torchaudio.functional.resample(tensor, sr, target_sr)
        data = resampled.T.numpy()
        sr = target_sr
        logger.debug("Resampled to %s Hz", target_sr)
    return data.astype(np.float32), sr


def write_audio(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    sf.write(path, audio, sample_rate)
    logger.debug("Wrote audio %s shape %s @ %s Hz", path, audio.shape, sample_rate)


def peak_normalize(audio: np.ndarray, peak_db: float = -1.0) -> np.ndarray:
    peak = float(np.max(np.abs(audio)))
    if peak == 0:
        return audio
    target = 10 ** (peak_db / 20)
    return audio * (target / peak)


def _match_channels(src: np.ndarray, target_channels: int) -> np.ndarray:
    if src.shape[1] == target_channels:
        return src
    if src.shape[1] == 1 and target_channels > 1:
        return np.repeat(src, target_channels, axis=1)
    return src[:, :target_channels]


def _align_length(src: np.ndarray, target_length: int) -> np.ndarray:
    if src.shape[0] == target_length:
        return src
    if src.shape[0] > target_length:
        return src[:target_length]
    pad = np.zeros((target_length - src.shape[0], src.shape[1]), dtype=src.dtype)
    return np.concatenate([src, pad], axis=0)


def subtract_vocals(original: np.ndarray, vocals: np.ndarray, strength: float) -> np.ndarray:
    # allow over-subtraction (e.g., 1.2+) to push residuals down; cap generously
    strength = float(np.clip(strength, 0.0, 2.0))
    vocals = _match_channels(vocals, original.shape[1])
    vocals = _align_length(vocals, original.shape[0])
    return original - strength * vocals
