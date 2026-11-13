# lite-bci-mcp

A simplified MCP server that lets Claude read and explain EEG brain state. 

The EEG signal goes through a small pipeline (filter, band powers, metrics), and Claude reads the results through three tools.

The design is adapted from [bci-mcp](https://github.com/enkhbold470/bci-mcp) by enkhbold470. This is our own simplified rebuild.

## How it works

```
EEG signal -> bandpass filter -> band powers -> metrics -> MCP tools -> Claude
```

1. **Signal.** A NumPy array of EEG samples plus its sampling rate. It comes from a synthetic generator, a recorded dataset, or a Muse 2 headset.
2. **Filtering.** A SciPy bandpass filter keeps 1 to 45 Hz.
3. **Band powers.** Welch's method (2 second windows, 50% overlap) gives the power in each band: delta (1-4 Hz), theta (4-8), alpha (8-13), beta (13-30), gamma (30-45).
4. **Metrics.** Ratios of band powers, listed below.
5. **MCP server.** FastMCP exposes the results to Claude Desktop as tools.

## Metrics

These are rough proxies from band power ratios, not clinical measures.

$$\text{focus} = \frac{\beta}{\alpha + \theta} \qquad \text{calm} = \frac{\alpha}{\alpha + \beta} \qquad \text{fatigue} = \frac{\theta + \alpha}{\beta}$$

- **Focus** is the engagement index from Pope, Bogart & Bartolome (1995).
- **Calm** is not a formally published index. We follow bci-mcp, which treats high alpha relative to beta as a rough correlate of relaxation.
- **Fatigue** follows Eoh et al. (2005), as cited in the bci-mcp documentation. It can read high when someone is simply relaxed, because strong alpha and weak beta look "fatigued" to the formula.

## MCP tools

| Tool | What it returns |
|---|---|
| `get_band_powers` | Power in each EEG band |
| `get_brain_state` | Focus, calm, and fatigue scores, plus the data source |
| `get_signal_quality` | A basic check for a flat signal, plus the sampling rate |

The tools take an optional `state` argument (`relaxed`, `focused`, or `neutral`) that only applies to synthetic data.

## Data sources

| Source | What it is | Used for |
|---|---|---|
| Synthetic | EEG made by our own code (sine waves at known frequencies plus noise) | Building and testing the pipeline, since the right answer is known |
| [PhysioNet EEG Motor Movement/Imagery Dataset](https://physionet.org/content/eegmmidb/1.0.0/) | Real recordings from 109 volunteers, including eyes open and eyes closed baselines | Checking the pipeline on real brains |
| Muse 2 (via BrainFlow) | Live EEG from a headset | Live demo |

The data source is chosen in `latest_chunk` in `server.py`, so the filter, metrics, and tools work the same with any of them. Set the environment variable `BCI_SOURCE` to `synthetic` (default) or `muse`.

## Setup

You need Python 3.10 or newer.

```bash
git clone https://github.com/nazaninean/lite-bci-mcp.git
cd lite-bci-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For the Muse 2 option, also run `pip install brainflow`.

## Run the tests

```bash
python test_synthetic.py   # pipeline checks on synthetic EEG
python test_server.py      # calls the MCP tools directly, no Claude needed
```

## Connect to Claude Desktop

In Claude Desktop, go to Settings, then Developer, then Edit Config, and add this (use the full paths to your own copy of the repo):

```json
{
  "mcpServers": {
    "lite-bci-mcp": {
      "command": "/full/path/to/lite-bci-mcp/.venv/bin/python",
      "args": ["/full/path/to/lite-bci-mcp/server.py"]
    }
  }
}
```

To use the Muse 2 instead of synthetic data, add `"env": { "BCI_SOURCE": "muse" }` to the same block. Then quit Claude Desktop completely (Cmd+Q) and reopen it. In a new chat, try: "What's my brain state if I'm relaxed? Now try focused."

## Files

| File | Purpose |
|---|---|
| `dsp.py` | Synthetic EEG generator, bandpass filter, Welch band powers |
| `metrics.py` | Focus, calm, and fatigue formulas |
| `server.py` | FastMCP server and data source switch |
| `data.py` | Loading recorded data (PhysioNet) |
| `test_synthetic.py` | Correctness checks on synthetic EEG |
| `test_server.py` | Calls the tools without Claude Desktop |

## Limitations
add this later

## References
add this later
