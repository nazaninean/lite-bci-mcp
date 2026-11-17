import time

import numpy as np
from pylsl import StreamInfo, StreamOutlet

FS = 256
# Same shape as the real thing, type "EEG" with 5 channels at 256 Hz
info = StreamInfo("FakeMuse", "EEG", 5, FS, "float32", "fake-muse-1")
outlet = StreamOutlet(info)

start = time.time()
n = 0
print("publishing a fake EEG stream, press Ctrl+C to stop")
while True:
    # Send as many samples as should exist by now, so the rate stays at 256 Hz
    target = int((time.time() - start) * FS)
    while n < target:
        t = n / FS
        alpha = 20 * np.sin(2 * np.pi * 10 * t)
        outlet.push_sample([alpha + np.random.randn() for _ in range(5)])
        n += 1
    time.sleep(0.01)