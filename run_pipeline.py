from data import check_recording, load_recording
from dsp import band_powers
from metrics import calm, fatigue, focus

def process_recording(subject, run, channel="Oz"):
    """run pipeline on 1 physionet recording

    run 1 is EO, run 2 is EC
    returns dict with band powers and metric scores
    raise ValueError if recording fails checks in data.py.
    """
    # load recording (from data.py)
    signal, fs = load_recording(subject, run, channel)

    # skip recs with wrong sampling rate/length
    problems = check_recording(signal, fs)
    if problems:
        raise ValueError(f"subject {subject} run {run}: {problems}")

    # apply bandpass filter and power (from dsp.py)
    powers = band_powers(signal, fs)

    # metric scores (formulas in metrics.py)
    return {
        "powers": powers,
        "focus": focus(powers),
        "calm": calm(powers),
        "fatigue": fatigue(powers),
    }

if __name__ == "__main__":
    for run, label in [(1, "eyes open"), (2, "eyes closed")]:
        result = process_recording(1, run)
        print(label, result)