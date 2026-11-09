from dsp import generate_eeg, band_powers

sig = generate_eeg(duration=10, amps={"alpha": 1.0}, noise=0.1, seed=0)
powers = band_powers(sig)
total = sum(powers.values())
for band, power in powers.items():
    print(f"{band}: {power / total:.1%}")