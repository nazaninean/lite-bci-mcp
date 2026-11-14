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
    board_id = BoardIds.MUSE_2_BOARD.value  # our headset is a Muse 2

    # First call only. Connect over Bluetooth and start collecting data.
    if _board is None:
        _board = BoardShim(board_id, BrainFlowInputParams())
        _board.prepare_session()  # connects to the headset
        _board.start_stream()     # keeps filling a buffer in the background
        time.sleep(seconds + 1)   # wait for the buffer to fill up
        logging.info("Muse 2 connected")

    # Muse 2 samples at 256 Hz, different from PhysioNet's 160 Hz,
    # so ask BrainFlow for the real value
    fs = BoardShim.get_sampling_rate(board_id)

    # Grab the newest samples from the buffer without clearing it, which
    # gives a rolling "live" window. Rows are channels, columns are samples.
    data = _board.get_current_board_data(int(seconds * fs))

    # take only the rows that hold EEG then average them into one signal.
    eeg_rows = BoardShim.get_eeg_channels(board_id)
    return data[eeg_rows].mean(axis=0), fs

def latest_chunk(state="neutral"):
    """Return (signal, sampling_rate) for the latest 4 seconds of EEG"""
    # Real headset
    if SOURCE == "muse":
        return muse_chunk()
    
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