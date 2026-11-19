import os
import time

from dsp import band_powers
from metrics import calm
from server import latest_chunk

# prints a reading every 2 seconds for 40 seconds
# keep your eyes open for the first 10, close them for 10, then open them again. Be still!
print("source:", os.environ.get("BCI_SOURCE", "synthetic"))
for i in range(20):
    sig, fs = latest_chunk()
    p = band_powers(sig, fs)
    share = p["alpha"] / sum(p.values())
    print(f"{i * 2:>2} s  alpha share {share:.2f}  calm {calm(p):.2f}  std {sig.std():.1f}")
    time.sleep(2)