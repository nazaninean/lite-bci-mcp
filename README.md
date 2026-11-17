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
1. The metrics used in this project are rough proxies and are not clinical
2. Muse headset only provides data for 4 channels and the quality might not be as good as conventional clinical grade EEG due to conductivity and channel number limitations
3. This version of the code is currently only available to be paired with a Muse 2 headset, further addition of other consumer EEG device models is a possible update

## References
- Barry, R. J., Clarke, A. R., Johnstone, S. J., Magee, C. A., & Rushby, J. A. (2007). EEG differences between eyes-closed and eyes-open resting conditions. Clinical Neurophysiology, 118(12), 2765–2773. https://doi.org/10.1016/j.clinph.2007.07.028  
- CircuitsComputers, E. (n.d.). Bci-mcp: Stream Live EEG Brain State Into Claude Over MCP. Instructables. Retrieved November 1, 2026, from https://www.instructables.com/Bci-mcp-Stream-Live-EEG-Brain-State-Into-Claude-Ov/  
- Ehtesham, A., Singh, A., Gupta, G. K., & Kumar, S. (2025). A survey of agent interoperability protocols: Model Context Protocol (MCP), Agent Communication Protocol (ACP), Agent-to-Agent Protocol (A2A), and Agent Network Protocol (ANP) (arXiv:2505.02279). arXiv. https://doi.org/10.48550/arXiv.2505.02279  
- Enkhbold470/bci-mcp: Stream live EEG brain state (focus, calm, attention) from any EEG device into Claude and any MCP client—A real Model Context Protocol server + brain-computer interface toolkit. (n.d.). Retrieved November 1, 2026, from https://github.com/enkhbold470/bci-mcp   
- Lim, W. L., Sourina, O., & Wang, L. P. (2018). STEW: Simultaneous Task EEG Workload Data Set. IEEE Transactions on Neural Systems and Rehabilitation Engineering, 26(11), 2106–2114. https://doi.org/10.1109/TNSRE.2018.2872924  
- Mikhaylov, D., Saeed, M., Husain Alhosani, M., & F. Al Wahedi, Y. (2024). Comparison of EEG Signal Spectral Characteristics Obtained with Consumer- and Research-Grade Devices. Sensors, 24(24), 8108. https://doi.org/10.3390/s24248108  
- Pope, A. T., Bogart, E. H., & Bartolome, D. S. (1995). Biocybernetic system evaluates indices of operator engagement in automated task. Biological Psychology, EEG in Basic and Applied Settings, 40(1), 187–195. https://doi.org/10.1016/0301-0511(95)05116-3  
- Schalk, G. (2009). EEG Motor Movement/Imagery Dataset. PhysioNet. https://doi.org/10.13026/C28G6P  
- Wang, J., & Wang, M. (2021). Review of the emotional feature extraction and classification using EEG signals. Cognitive Robotics, 1, 29–40. https://doi.org/10.1016/j.cogr.2021.04.001  
- Welcome to BrainFlow’s documentation! —BrainFlow documentation. (n.d.). Retrieved November 2, 2026, from https://brainflow.readthedocs.io/en/stable/ 
