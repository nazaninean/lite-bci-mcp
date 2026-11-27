import os
import sys
from math import isfinite
from statistics import median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon

from metrics import relative_alpha
from run_pipeline import process_recording

SUBJECTS = range(1, 21)
CHANNEL = sys.argv[1] if len(sys.argv) > 1 else "Oz"

os.makedirs("results", exist_ok=True)


def measures(result):
    """The two measures for one recording."""
    return {
        "relative_alpha": relative_alpha(result["powers"]),
        "calm": result["calm"],
    }


# pairs[measure] is a list of (subject, open_value, closed_value)
pairs = {"relative_alpha": [], "calm": []}
skipped = []

for subject in SUBJECTS:
    try:
        # Run 1 = eyes open, run 2 = eyes closed
        open_values = measures(process_recording(subject, run=1, channel=CHANNEL))
        closed_values = measures(process_recording(subject, run=2, channel=CHANNEL))
    except Exception as error:
        skipped.append(f"subject {subject}: {error}")
        continue

    # Keep a subject only if every value is a real number, so each pair is complete
    if not all(isfinite(v) for v in [*open_values.values(), *closed_values.values()]):
        skipped.append(f"subject {subject}: a value was not finite")
        continue

    for name in pairs:
        pairs[name].append((subject, open_values[name], closed_values[name]))

lines = [f"Channel {CHANNEL}, subjects {SUBJECTS.start} to {SUBJECTS.stop - 1}"]
lines.append(f"Kept {len(pairs['relative_alpha'])} subjects, skipped {len(skipped)}")
lines.extend(f"  skipped {s}" for s in skipped)

for name, rows in pairs.items():
    lines.append("")
    lines.append(f"{name}")
    n = len(rows)
    if n < 2:
        lines.append("  Too few valid pairs. Test skipped.")
        continue

    open_ = [o for _, o, _ in rows]
    closed = [c for _, _, c in rows]
    diffs = [c - o for c, o in zip(closed, open_)]
    higher = sum(d > 0 for d in diffs)

    lines.append(f"  n = {n}")
    lines.append(f"  median open = {median(open_):.4f}, median closed = {median(closed):.4f}")
    lines.append(f"  median difference (closed - open) = {median(diffs):.4f}")
    lines.append(f"  {higher} of {n} higher with eyes closed")

    if all(d == 0 for d in diffs):
        lines.append("  All differences are zero. Test skipped.")
    else:
        result = wilcoxon(closed, open_, alternative="two-sided")
        lines.append(f"  Wilcoxon statistic = {result.statistic:.4g}, p = {result.pvalue:.4g}")

    # paired line plot, one gray line per subject, median in color
    plt.figure(figsize=(4, 5))
    for o, c in zip(open_, closed):
        plt.plot([0, 1], [o, c], color="gray", alpha=0.5)
    plt.plot([0, 1], [median(open_), median(closed)], color="#C8694A", linewidth=3, label="median")
    plt.xticks([0, 1], ["eyes open", "eyes closed"])
    plt.ylabel(name)
    plt.title(f"{name}, channel {CHANNEL} (n = {n})")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"results/{name}_{CHANNEL}_open_vs_closed.png", dpi=200)
    plt.close()

text = "\n".join(lines)
print(text)
with open(f"results/summary_{CHANNEL}.txt", "w") as f:
    f.write(text + "\n")