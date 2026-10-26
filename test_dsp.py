import matplotlib.pyplot as plt
from dsp import generate_eeg, FS

sig = generate_eeg(duration=5, amps={"alpha": 1.0}, noise=0.1, seed=0)
plt.plot(sig[:2 * FS])
plt.xlabel("sample")
plt.ylabel("amplitude")
plt.savefig("alpha_test.png")
print("saved alpha_test.png")