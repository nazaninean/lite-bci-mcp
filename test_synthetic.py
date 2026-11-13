# Checks that our pipeline gives the right answers on synthetic EEG, where we
# know the correct answer in advance

# Test 1: we make 10 seconds of EEG at 160 Hz with a single
# sine wave (delta at 2 Hz, theta at 6 Hz, alpha at 10 Hz, beta at 20 Hz,
# gamma at 35 Hz) plus a little noise (0.1), then check that the band with the
# most power is the one we put in. Right now each lands in its own band with
# about 99% of the total power.

# Test 2 (metric formulas): we use made up band powers (theta = 1, alpha = 2,
# beta = 3) and check the code gives the answers worked out by hand. Focus
# should be 3 divided by (2 + 1) = 1.0, calm should be 2 divided by (2 + 3) =
# 0.4, and fatigue should be (1 + 2) divided by 3 = 1.0.

# Test 3 (Muse sampling rate): we repeat the alpha test at 256 Hz, the Muse 2
# sampling rate, and check alpha still has over 90% of the power (we get
# about 99.5%). This shows the code does not only work at PhysioNet's 160 Hz.


from dsp import CENTERS, band_powers, generate_eeg
from metrics import calm, fatigue, focus

# Test 1: a signal with only one band should land in that band
for band in CENTERS:
    sig = generate_eeg(duration=10, amps={band: 1.0}, noise=0.1, seed=0)
    p = band_powers(sig)
    top = max(p, key=p.get)
    share = p[top] / sum(p.values())
    print(f"{band} alone -> top band is {top} ({share:.1%})")
    assert top == band, f"{band} landed in {top}"

# Test 2: metrics against numbers worked out by hand
p = {"delta": 0, "theta": 1, "alpha": 2, "beta": 3, "gamma": 0}
assert abs(focus(p) - 1.0) < 1e-9    # 3 divided by (2 + 1)
assert abs(calm(p) - 0.4) < 1e-9     # 2 divided by (2 + 3)
assert abs(fatigue(p) - 1.0) < 1e-9  # (1 + 2) divided by 3
print("metrics match the hand calculations")

# Test 3: a different sampling rate, like the Muse's 256 Hz
sig = generate_eeg(duration=10, fs=256, amps={"alpha": 1.0}, noise=0.1, seed=0)
p = band_powers(sig, fs=256)
share = p["alpha"] / sum(p.values())
print(f"alpha alone at 256 Hz -> alpha share {share:.1%}")
assert share > 0.9

print("all synthetic checks passed")