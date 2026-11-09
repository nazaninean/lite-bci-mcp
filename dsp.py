import numpy as np
from scipy.signal import butter, filtfilt, welch

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
    "Make a synthetic EEG signal by mixing one sine wave per band plus noise."
    rng = np.random.default_rng(seed)
    amps = amps or {band: 1.0 for band in CENTERS}
    t = np.arange(int(duration * fs)) / fs
    signal = np.zeros_like(t)
    for band, freq in CENTERS.items():
        signal += amps.get(band, 0) * np.sin(2 * np.pi * freq * t)
    return signal + noise * rng.standard_normal(len(t))

def bandpass(signal, low=1, high=45, fs=FS, order=4):
    "Keep only frequencies between low and high (Hz)."
    nyquist = fs * 0.5
    b, a = butter(order, [low / nyquist, high / nyquist], btype="band")
    return filtfilt(b, a, signal)

def band_powers(signal, fs=FS):
    "Filter the signal, then return the power in each frequency band."
    filtered = bandpass(signal, fs=fs)
    # 2 second windows with 50% overlap
    freqs, psd = welch(filtered, fs=fs, nperseg=2 * fs, noverlap=fs)
    step = freqs[1] - freqs[0]
    powers = {}
    for band, (lo, hi) in BANDS.items():
        mask = (freqs >= lo) & (freqs < hi)
        powers[band] = float(psd[mask].sum() * step)
    return powers