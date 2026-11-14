import mne
from mne.datasets import eegbci

def load_recording(subject, run, channel="Oz"):
    """load 1 physionet recording and return (signal, sampling_rate).

    subject is a number from 1 to 109.
    run 1 is the EO baseline, run 2 is the EC baseline
    """
    # downloads the file to our comp
    path = eegbci.load_data(subject, runs=[run])[0]

    # read the file into memory
    raw = mne.io.read_raw_edf(path, preload=True, verbose=False)

    # standardize the name from something like "Oz.." to "Oz" works
    eegbci.standardize(raw)

    # pull 1 channel as a numpy array
    # multiply by 1e6 to get microvolts.
    signal = raw.get_data(picks=[channel])[0] * 1e6

    # sampling rate should be 160 for every file in this dataset
    return signal, raw.info["sfreq"]


def check_recording(signal, fs):
    """return a list of problems (empty means it looks fine). we skip and log any subject that fails"""
    problems = []
    if fs != 160:
        problems.append(f"sampling rate is {fs}, expected 160")
    seconds = len(signal) / fs
    if not 55 <= seconds <= 65:
        problems.append(f"length is {seconds:.0f} s, expected about 60")
    return problems