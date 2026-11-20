# lite-bci-mcp for Muse 2

A simplified MCP server that lets Claude read and explain EEG brain state, built for the Muse 2 headset.

The EEG signal goes through a small pipeline (filter, band powers, metrics), and Claude reads the results through three tools. Claude never sees the raw EEG, only the numbers the pipeline produces.

The design is adapted from [bci-mcp](https://github.com/enkhbold470/bci-mcp) by enkhbold470. This is our own simplified rebuild and it works for Muse 2 specifically.

## How it works

```
Muse 2 (or synthetic / recorded EEG) -> bandpass filter -> band powers -> metrics -> MCP tools -> Claude
```

1. **Signal.** A NumPy array of EEG samples plus its sampling rate. It comes from a Muse 2 headset, a synthetic generator, or a recorded dataset.
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

| Source | `BCI_SOURCE` | What it is | Used for |
|---|---|---|---|
| Synthetic | `synthetic` (default) | EEG made by our own code (sine waves at known frequencies plus noise) | Building and testing the pipeline, since the right answer is known |
| Muse 2 through LSL | `muse_lsl` | Live EEG, streamed by `muselsl` and read with `pylsl` | Live demo (the route we use) |
| Muse 2 through BrainFlow | `muse` | Live EEG, read directly with BrainFlow | Written, but BrainFlow often failed to find our headset, so we use LSL |
| [PhysioNet EEG Motor Movement/Imagery Dataset](https://physionet.org/content/eegmmidb/1.0.0/) | not used by the server | Real recordings from 109 volunteers, including eyes open and eyes closed baselines | Checking the pipeline on real brains |

The data source is chosen in `latest_chunk` in `server.py`, so the filter, metrics, and tools work the same with any of them.

## Setup

You need Python 3.10 or newer.

```bash
git clone https://github.com/nazaninean/lite-bci-mcp.git
cd lite-bci-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` includes `muselsl`, `pylsl`, and `bitstring<5`. The `bitstring<5` pin matters, because `muselsl` crashes with `bitstring` 5 ("The 'bytes' keyword has been removed").

Check that everything works on simulated data first:

```bash
python test_synthetic.py   # pipeline checks on synthetic EEG
python test_server.py      # calls the MCP tools directly, no Claude needed
```

## Connect to Claude Desktop (simulated data)

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

Quit Claude Desktop completely (Cmd+Q) and reopen it. In a new chat, try: "What's my brain state?" The reading says `source: synthetic`.

## Use a Muse 2 (live)

This uses LSL (Lab Streaming Layer). `muselsl` connects to the Muse 2 and publishes its EEG as an LSL stream, and the server reads that stream.

**1. Get the headset ready.**
- Charge it and turn it on until the light blinks.
- Close the Muse app on any phone and turn that phone's Bluetooth off, because a Muse can only connect to one device.
- If other Muse headsets are nearby, ask their owners to turn them off.
- Put it on with the forehead sensors on clean skin and the sensors behind the ears touching skin, with hair out of the way.

**2. Find your headset's name.**

```bash
muselsl list
```

Run it two or three times, since Bluetooth scans sometimes miss devices. It prints names like `Muse-1A2B`. macOS may ask for Bluetooth permission the first time, so allow it.

**3. Start the stream and leave it running.**

```bash
muselsl stream --name Muse-1A2B
```

It should say it's streaming, and the light on the headset changes. Keep this terminal open the whole time.

**4. Test the server's reader in a second terminal** (with `(.venv)` active):

```bash
BCI_SOURCE=muse_lsl python -c "from server import latest_chunk; sig, fs = latest_chunk(); print(len(sig), fs, sig.std())"
```

Success looks like `1024 256.0` and a number above 0. A number near 0 means the sensors aren't touching skin.

**5. Check the signal is real.**

```bash
BCI_SOURCE=muse_lsl python live_check.py
```

It prints a reading every 2 seconds for 40 seconds. Keep your eyes open for the first 10 seconds, close them for 10, then open them again. Sit still, because blinks and jaw clenching add spikes. Alpha share and calm should usually go up with eyes closed. A Muse has no sensor at the back of the head, where alpha is strongest, so the change can be smaller than in the PhysioNet recordings.

**6. Connect Claude Desktop to the live stream.** Add an `env` line to the server block in the config (mind the comma after `args`), then quit and reopen Claude Desktop with Cmd+Q. Keep `muselsl stream` running.

```json
"lite-bci-mcp": {
  "command": "/full/path/to/lite-bci-mcp/.venv/bin/python",
  "args": ["/full/path/to/lite-bci-mcp/server.py"],
  "env": { "BCI_SOURCE": "muse_lsl" }
}
```

In a new chat, ask for your brain state. The reading should say `source: muse_lsl`. When you're done, remove the `env` line to go back to simulated data, stop `muselsl stream` with Ctrl+C, and turn off the headset.

**Test the LSL reader without a headset.** `fake_lsl_stream.py` publishes a fake Muse-style stream with a 10 Hz alpha wave. Run `python fake_lsl_stream.py` in one terminal and step 4 in another, and you should see `1024 256.0` with alpha far larger than the other bands. Stop it with Ctrl+C before connecting the real headset, because the server reads the first EEG stream it finds.

### Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `muselsl list` finds nothing | Turn the headset off for 10 seconds and on again, close the Muse app, and allow Bluetooth for your terminal or VS Code in System Settings, then Privacy & Security |
| `muselsl stream` crashes with "The 'bytes' keyword has been removed" | Run `pip install "bitstring<5"` |
| The server says no LSL EEG stream was found | `muselsl stream` isn't running yet, or hasn't finished connecting |
| The reading mentions `FakeMuse` | `fake_lsl_stream.py` is still running, so stop it and restart the server |
| Same numbers every time | The server is in simulated mode, so check `source` in the reading |
| Switched streams but the server still reads the old one | The server remembers its first connection, so quit and reopen Claude Desktop (Cmd+Q) |
| A flat signal (std near 0) | The sensors aren't touching skin |

### Why LSL and not BrainFlow

Both routes get EEG samples from the Muse into `latest_chunk` in `server.py`. Everything after that (filter, band powers, metrics, tools) is the same.

**BrainFlow** (`BCI_SOURCE=muse`, needs `pip install brainflow`) talks to the headset directly. One Python package handles the Bluetooth connection and decoding, and it has a built-in fake board for testing without a headset. We tried it first because bci-mcp uses it for the Muse. In our setup it often failed with "Failed to find Muse Device" after a short Bluetooth scan, in a room with dozens of Bluetooth devices. We extended the scan to 30 seconds and added a `BCI_MUSE_SERIAL` setting to pick one headset (for example `Muse-1A2B`), but did not get to confirm that fixes it. This does not mean BrainFlow cannot work, only that it was not reliable for us.

**LSL** (`BCI_SOURCE=muse_lsl`) splits the job in two. `muselsl` connects to the Muse and publishes its EEG as an LSL stream, and our server reads that stream with `pylsl` and never touches Bluetooth. We switched because:
- `muselsl list` found our headset right away.
- The other groups that paired their Muse successfully used LSL.
- It is easier to debug. If `muselsl stream` connects, the headset is fine, so any later failure is in our code.
- We can test the server without a headset using `fake_lsl_stream.py`.

The cost is an extra terminal that has to stay open, and `muselsl` is less actively maintained, which is why `bitstring` needs to be pinned below version 5.

`BCI_BOARD=synthetic` switches the BrainFlow route to its built-in fake board, which is useful for testing that code without a headset.

## Data analysis (PhysioNet)

To check the pipeline on real EEG, we compare eyes open and eyes closed baseline recordings from PhysioNet. Alpha power at the back of the head is known to be higher with eyes closed (the Berger effect), so the pipeline should find it. This is a positive control. It tests the pipeline, not whether "calm" measures psychological calm.

- Data: runs 1 (eyes open) and 2 (eyes closed), first 20 subjects, channel Oz.
- Main measure: relative alpha, alpha power divided by total power across the five bands. Calm is the second measure.
- Test: paired Wilcoxon signed-rank test on (eyes closed minus eyes open).
- Files: `data.py`, `run_pipeline.py`, `analysis.py`. See `ANALYSIS_PLAN.md` and `TASKS.md` for the plan and task split.

## Files

| File | Purpose |
|---|---|
| `dsp.py` | Synthetic EEG generator, bandpass filter, Welch band powers |
| `metrics.py` | Focus, calm, and fatigue formulas |
| `server.py` | FastMCP server and data source switch (synthetic, Muse through LSL, Muse through BrainFlow) |
| `data.py` | Loading PhysioNet recordings |
| `run_pipeline.py` | Runs recordings through the pipeline |
| `analysis.py` | Eyes open vs. eyes closed statistics and plots |
| `live_check.py` | Prints live readings for 40 seconds, to check a real headset |
| `fake_lsl_stream.py` | Publishes a fake Muse-style LSL stream for testing without a headset |
| `test_synthetic.py` | Correctness checks on synthetic EEG |
| `test_server.py` | Calls the tools without Claude Desktop |

## Limitations
add later

## References

- Pope, A. T., Bogart, E. H., & Bartolome, D. S. (1995). Biocybernetic system evaluates indices of operator engagement in automated task. *Biological Psychology*, 40(1-2), 187-195.
- Eoh et al. (2005), as cited in the bci-mcp documentation.
- enkhbold470. bci-mcp [Software]. https://github.com/enkhbold470/bci-mcp
- Schalk, G., McFarland, D. J., Hinterberger, T., Birbaumer, N., & Wolpaw, J. R. (2004). BCI2000: A general-purpose brain-computer interface (BCI) system. *IEEE Transactions on Biomedical Engineering*.
- Goldberger, A. L., et al. (2000). PhysioBank, PhysioToolkit, and PhysioNet. *Circulation*, 101(23), e215-e220.
- Welch, P. (1967). The use of fast Fourier transform for the estimation of power spectra. *IEEE Transactions on Audio and Electroacoustics*, 15(2), 70-73.
