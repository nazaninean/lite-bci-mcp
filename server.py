import atexit
import logging
import os
import sys
import time

# FastMCP turns the Python functions into tools that claude can call
from fastmcp import FastMCP

from dsp import FS, band_powers, generate_eeg

from metrics import calm, fatigue, focus

# Send log messages to stderr instead of stdout so logs show up in claude desktop's logs.
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# Create the server
mcp = FastMCP("lite-bci-mcp")

# Which data source to use, "synthetic" or "muse".
# Set later in the Claude Desktop config under "env"
SOURCE = os.environ.get("BCI_SOURCE", "synthetic")

# Presets for the simulated signal
STATES = {
    "relaxed": {"alpha": 3.0, "beta": 0.5},  # strong alpha, weak beta
    "focused": {"alpha": 0.5, "beta": 3.0},  # weak alpha, strong beta
    "neutral": {},                           # every band at the default
}

_board = None  # Muse connection, opened once on first use

def close_muse():
    """Stop streaming and disconnect the Muse, so the headset is released
    when the server shuts down."""
    global _board
    if _board is not None:
        try:
            _board.stop_stream()
            _board.release_session()
        except Exception as error:
            logging.warning("Could not close Muse cleanly: %s", error)
        _board = None

# Run close_muse automatically when the server exits
atexit.register(close_muse)

def muse_chunk(seconds=4):
    """Read the newest few seconds of EEG from our Muse 2 through BrainFlow.
    Returns the signal and its sampling rate."""
    # Imported here so the server still runs without brainflow installed
    from brainflow.board_shim import BoardShim, BoardIds, BrainFlowInputParams

    global _board
    ##board_id = BoardIds.MUSE_2_BOARD.value  # our headset is a Muse 2
    if os.environ.get("BCI_BOARD") == "synthetic":
        board_id = BoardIds.SYNTHETIC_BOARD.value
    else:
        board_id = BoardIds.MUSE_2_BOARD.value

    # First call only. Connect over Bluetooth and start collecting data.
    if _board is None:
        params = BrainFlowInputParams()
        # Scan for up to 30 seconds. The default is 6, which is too short
        # in a room full of Bluetooth devices.
        params.timeout = 30
        # Connect to one specific headset, like "Muse-3724"
        serial = os.environ.get("BCI_MUSE_SERIAL")
        if serial:
            params.serial_number = serial
        board = BoardShim(board_id, params)
        try:
            board.prepare_session()  # raises an error if it can't connect
            board.start_stream()
            time.sleep(seconds + 1)  # wait for the buffer to fill up
        except Exception:
            # Release the headset so the next try starts clean
            try:
                board.release_session()
            except Exception:
                pass
            raise
        # Only save the board once the connection worked
        _board = board
        logging.info("Muse 2 connected")

    # Muse 2 samples at 256 Hz, so ask BrainFlow for the real value
    fs = BoardShim.get_sampling_rate(board_id)

    # Grab the newest samples from the buffer without clearing it
    data = _board.get_current_board_data(int(seconds * fs))

    # Keep only the EEG rows, then average the channels into one signal
    eeg_rows = BoardShim.get_eeg_channels(board_id)
    return data[eeg_rows].mean(axis=0), fs

# The LSL connection
_inlet = None
_lsl_window = None  # rolling window that holds the most recent samples


def lsl_chunk(seconds=4):
    """Read the newest few seconds of EEG from an LSL stream (made by
    muselsl). Returns the signal and its sampling rate."""
    from collections import deque

    import numpy as np
    from pylsl import StreamInlet, resolve_byprop

    global _inlet, _lsl_window

    # First call only. Find the EEG stream and open it.
    if _inlet is None:
        streams = resolve_byprop("type", "EEG", timeout=15)
        if not streams:
            raise RuntimeError(
                "No LSL EEG stream found. Start one first with: "
                "muselsl stream --name Muse-XXXX"
            )
        _inlet = StreamInlet(streams[0], max_buflen=30)
        fs = _inlet.info().nominal_srate()
        _lsl_window = deque(maxlen=int(seconds * fs))
        logging.info("Connected to LSL stream %s at %s Hz", _inlet.info().name(), fs)

    fs = _inlet.info().nominal_srate()

    # Keep pulling until the window is full, or give up after a while
    deadline = time.time() + seconds + 10
    while True:
        # Pull everything that arrived since the last call. Old samples fall
        # off the front of the deque, so the window is always the newest ones.
        samples, _ = _inlet.pull_chunk(timeout=0.0, max_samples=20000)
        if samples:
            rows = np.array(samples)
            # Muse 2 sends 4 EEG channels plus an AUX channel, so keep the
            # first 4 and average them into one signal
            eeg = rows[:, : min(4, rows.shape[1])]
            _lsl_window.extend(eeg.mean(axis=1))
        if len(_lsl_window) >= _lsl_window.maxlen:
            break
        if time.time() > deadline:
            raise RuntimeError("Not enough EEG data arriving from the LSL stream")
        time.sleep(0.2)

    return np.array(_lsl_window), fs

def latest_chunk(state="neutral"):
    """Return (signal, sampling_rate) for the latest 4 seconds of EEG"""
    # Real headset
    if SOURCE == "muse":
        return muse_chunk()
    if SOURCE == "muse_lsl":
        return lsl_chunk()
    
# simulated data. Start with every band at the default amplitude of 1.0.
    amps = {band: 1.0 for band in ["delta", "theta", "alpha", "beta", "gamma"]}
    # Apply the chosen preset on top
    amps.update(STATES.get(state, {}))
    # Make 4 seconds of synthetic EEG with those amplitudes plus noise
    return generate_eeg(duration=4, amps=amps, noise=0.5), FS

# @mcp.tool() below registers the function as a tool. Claude reads
# the docstring to decide when to use it and what the inputs mean
@mcp.tool()
def get_band_powers(state: str = "neutral") -> dict:
    """Return power in each EEG band (delta, theta, alpha, beta, gamma)"""
    # Get the latest chunk, then filter it and measure power in each band
    sig, fs = latest_chunk(state)
    return band_powers(sig, fs)

@mcp.tool()
def get_brain_state(state: str = "neutral") -> dict:
    """Return focus, calm, and fatigue scores computed from the latest EEG chunk"""
    # Band powers
    sig, fs = latest_chunk(state)
    p = band_powers(sig, fs)
    # Round to 3 decimals so the numbers are easy for Claude to read out
    return {
        "source": SOURCE,  # "synthetic" or "muse", so Claude knows where the data came from
        "focus": round(focus(p), 3),
        "calm": round(calm(p), 3),
        "fatigue": round(fatigue(p), 3),
    }

@mcp.tool()
def get_signal_quality(state: str = "neutral") -> dict:
    """Return a simple signal quality check on the latest EEG chunk."""
    sig, fs = latest_chunk(state)
    # standard deviation measures how much the signal moves. A flat line
    # usually means a bad connection or a loose electrode.
    spread = float(sig.std())
    return {
        "quality": "good" if spread > 0.01 else "poor (flat signal)",
        "std": round(spread, 3),
        "sampling_rate_hz": fs,
    }

if __name__ == "__main__":
    mcp.run()