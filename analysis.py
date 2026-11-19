from math import isfinite
from statistics import median

from scipy.stats import wilcoxon

from run_pipeline import process_recording


def main():
    subjects = [1, 2, 3, 4, 5]  # Replace with your subject IDs
    differences = []

    for subject in subjects:
        try:
            # Run 1 = eyes open, run 2 = eyes closed
            eyes_open = process_recording(subject, run=1, channel="Oz")
            eyes_closed = process_recording(subject, run=2, channel="Oz")
        except ValueError as error:
            print(f"Skipping subject {subject}: {error}")
            continue

        alpha_open = eyes_open["powers"]["alpha"]
        alpha_closed = eyes_closed["powers"]["alpha"]

        # One difference per subject: eyes closed minus eyes open
        difference = alpha_closed - alpha_open
        if not isfinite(difference):
            print(f"Skipping subject {subject}: invalid alpha difference")
            continue

        differences.append(difference)

    print(f"Valid subject pairs: {len(differences)}")

    if len(differences) < 2:
        print("Too few valid pairs. Wilcoxon test skipped.")
        return

    print(f"Median difference (closed - open): {median(differences):.6g}")

    if all(difference == 0 for difference in differences):
        print("All differences are zero. Wilcoxon test skipped.")
        return

    # Run the test once, after collecting all paired differences
    result = wilcoxon(differences, alternative="two-sided")
    print(f"Wilcoxon statistic: {result.statistic:.6g}")
    print(f"p-value: {result.pvalue:.6g}")


if __name__ == "__main__":
    main()
