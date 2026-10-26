import numpy as np

FS = 160  # sampling rate in Hz, matching PhysioNet's

BANDS = {
    "delta": (1, 4),
    "theta": (4, 8),
    "alpha": (8, 13),
    "beta": (13, 30),
    "gamma": (30, 45),
}

# one center frequency per band for the synthetic signal
CENTERS = {"delta": 2, "theta": 6, "alpha": 10, "beta": 20, "gamma": 35}


def generate_eeg(duration=10, fs=FS, amps=None, noise=0.5, seed=None):
    """Make a synthetic EEG signal by mixing one sine wave per band plus noise."""
    rng = np.random.default_rng(seed)
    amps = amps or {band: 1.0 for band in CENTERS}
    t = np.arange(int(duration * fs)) / fs
    signal = np.zeros_like(t)
    for band, freq in CENTERS.items():
        signal += amps.get(band, 0) * np.sin(2 * np.pi * freq * t)
    return signal + noise * rng.standard_normal(len(t))