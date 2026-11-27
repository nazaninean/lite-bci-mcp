def focus(p):
    """Engagement index: beta power divided by (alpha power plus theta power).

    Source: Pope, A. T., Bogart, E. H., & Bartolome, D. S. (1995).
    Biocybernetic system evaluates indices of operator engagement in
    automated task. Biological Psychology, 40(1-2), 187-195.
    """
    return p["beta"] / (p["alpha"] + p["theta"])


def calm(p):
    """Relaxation proxy: alpha power divided by (alpha power plus beta power).

    Not a formally published index. Follows the bci-mcp project
    (https://github.com/enkhbold470/bci-mcp), which describes it as a
    long-standing relaxation correlate.
    """
    return p["alpha"] / (p["alpha"] + p["beta"])


def fatigue(p):
    """Fatigue proxy: (theta power plus alpha power) divided by beta power.

    Source: Eoh et al. (2005), as cited in the bci-mcp documentation.
    """
    return (p["theta"] + p["alpha"]) / p["beta"]

def relative_alpha(p):
    """Alpha power as a share of the total power across all five bands."""
    return p["alpha"] / sum(p.values())