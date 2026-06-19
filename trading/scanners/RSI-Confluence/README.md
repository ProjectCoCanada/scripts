# AGT Bitget Futures RSI Scanner

A lightweight, dependency-free Python script that continuously scans **Bitget futures markets** for assets showing **extreme RSI (Relative Strength Index)** readings, confirmed across two timeframes for higher-confidence signals.

It prints a live, color-coded-style terminal table of the top 25 matching assets by 24-hour volume, outputs the same data as JSON for easy piping into other tools, and plays an audible alert whenever new matches are found.

---

## Table of Contents

- [What This Script Does](#what-this-script-does)
- [How the Signal Logic Works](#how-the-signal-logic-works)
- [Requirements](#requirements)
- [Installation](#installation)
  - [macOS](#macos)
  - [Windows](#windows)
  - [Linux](#linux)
- [Running the Scanner](#running-the-scanner)
- [Configuration Options](#configuration-options)
- [Understanding the Output](#understanding-the-output)
- [Stopping the Scanner](#stopping-the-scanner)
- [Troubleshooting](#troubleshooting)
- [Disclaimer](#disclaimer)

---

## What This Script Does

On each scan cycle, the script:

1. **Fetches all active futures pairs** from Bitget (USDT-margined and/or USDC-margined, depending on your settings), along with their 24-hour trading volume.
2. **Calculates RSI** (14-period, Wilder's smoothing method) for each symbol on a configurable *primary* timeframe and a configurable *confluency* timeframe.
3. **Flags an asset** only when both timeframes agree — for example, both showing overbought, or both showing oversold — which helps filter out short-lived noise.
4. **Optionally calculates extra timeframes** purely for display/context (these do not affect which assets get flagged).
5. **Displays the top 25 matching assets**, sorted by 24-hour volume, in a clean terminal table plus a raw JSON block.
6. **Plays a sound alert** if any assets matched that scan.
7. **Repeats automatically** every N seconds (configurable) until you stop it.

Requests are fetched concurrently using a thread pool, so a full scan of all symbols typically completes in well under a minute.

---

## How the Signal Logic Works

- **Primary timeframe** (default `1H`): This is the trigger. An asset must show RSI ≥ `PRIMARY_OVERBOUGHT` (default 70) or RSI ≤ `PRIMARY_OVERSOLD` (default 30) here to even be considered.
- **Confluency timeframe** (default `4H`): This confirms the signal. The asset must *also* show RSI ≥ `CONFLUENCY_OVERBOUGHT` (default 60) or RSI ≤ `CONFLUENCY_OVERSOLD` (default 40) in the *same direction* as the primary signal.
- An asset is only flagged as **OVERBOUGHT** or **OVERSOLD** when both conditions align. If only one timeframe is extreme, it's filtered out.
- **Extra timeframes** (default `15m`, `30m`, `1D`) are calculated and shown in the table for additional context, but have no bearing on whether an asset is flagged.

---

## Requirements

- **Python 3.7 or newer** (no other version requirements)
- **An internet connection** (the script calls Bitget's public market-data API at `api.bitget.com` — no API key, account, or authentication needed)
- **No third-party packages required.** The script uses only Python's standard library (`urllib`, `json`, `time`, `sys`, `subprocess`, `concurrent.futures`, and `winsound` on Windows). There is nothing to `pip install`.

---

## Installation

### macOS

1. **Check if Python 3 is already installed.** Open **Terminal** (`Cmd + Space`, type "Terminal", press Enter) and run:
   ```bash
   python3 --version
   ```
   Recent versions of macOS often include Python 3, but if the command isn't found or the version is older than 3.7, install it:
   - **Option A — Homebrew (recommended):**
     ```bash
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
     brew install python3
     ```
   - **Option B — Official installer:** Download and run the macOS installer from [python.org/downloads](https://www.python.org/downloads/macos/).

2. **Save the script.** Place `RSIc.py` in a folder of your choice, e.g. `~/Downloads` or `~/scripts`.

3. **Navigate to that folder in Terminal:**
   ```bash
   cd ~/Downloads
   ```

4. **Run the script:**
   ```bash
   python3 RSIc.py
   ```

Sound alerts use the built-in `afplay` command, so no additional setup is needed for audio.

---

### Windows

1. **Install Python 3.** Download the installer from [python.org/downloads/windows](https://www.python.org/downloads/windows/). During installation, **check the box that says "Add Python to PATH"** before clicking Install — this step is important.

2. **Verify the install.** Open **Command Prompt** (search "cmd" in the Start menu) or **PowerShell** and run:
   ```cmd
   python --version
   ```
   If that command isn't recognized, try:
   ```cmd
   py --version
   ```

3. **Save the script.** Place `RSIc.py` in a folder, e.g. `C:\Users\YourName\Documents\RSIScanner`.

4. **Navigate to that folder:**
   ```cmd
   cd C:\Users\YourName\Documents\RSIScanner
   ```

5. **Run the script:**
   ```cmd
   python RSIc.py
   ```
   or, if `python` isn't recognized:
   ```cmd
   py RSIc.py
   ```

Sound alerts use the built-in `winsound` module, which ships with Python on Windows — no additional setup is required.

---

### Linux

1. **Check if Python 3 is installed** (most distributions include it by default):
   ```bash
   python3 --version
   ```

2. **If it's missing, install it** using your distro's package manager:
   - **Debian / Ubuntu:**
     ```bash
     sudo apt update && sudo apt install python3
     ```
   - **Fedora:**
     ```bash
     sudo dnf install python3
     ```
   - **Arch:**
     ```bash
     sudo pacman -S python
     ```

3. **(Optional) Enable sound alerts.** The script uses `paplay` for audio on Linux. If it's not already installed:
   - **Debian / Ubuntu:**
     ```bash
     sudo apt install pulseaudio-utils
     ```
   - **Fedora:**
     ```bash
     sudo dnf install pulseaudio-utils
     ```
   - **Arch:**
     ```bash
     sudo pacman -S libpulse
     ```
   If `paplay` isn't available, the script automatically falls back to a terminal bell beep, so this step is optional.

4. **Save the script** to a folder, e.g. `~/scripts`.

5. **Navigate to that folder:**
   ```bash
   cd ~/scripts
   ```

6. **Run the script:**
   ```bash
   python3 RSIc.py
   ```

---

## Running the Scanner

Once started, the script runs continuously: it performs a scan, displays results, waits for the configured interval, then scans again — automatically, with no further input needed.

**Optional: run in the background and log output (macOS/Linux):**
```bash
nohup python3 RSIc.py > scan_log.txt 2>&1 &
```

**Optional: save output to a file while still watching it live:**
```bash
python3 RSIc.py | tee scan_log.txt
```

---

## Configuration Options

All settings live near the top of `RSIc.py`, under the `CONFIGURATION` section. Open the file in any text editor to adjust them, then save and re-run.

| Variable | Default | Description |
|---|---|---|
| `SCAN_USDT_M` | `False` | Scan USDT-margined futures pairs |
| `SCAN_USDC_M` | `True` | Scan USDC-margined futures pairs |
| `PRIMARY_TIMEFRAME` | `"1H"` | Timeframe that must show extreme RSI to trigger a candidate flag |
| `PRIMARY_OVERBOUGHT` | `70` | RSI value (≥) considered overbought on the primary timeframe |
| `PRIMARY_OVERSOLD` | `30` | RSI value (≤) considered oversold on the primary timeframe |
| `CONFLUENCY_TIMEFRAME` | `"4H"` | Secondary timeframe used to confirm the primary signal |
| `CONFLUENCY_OVERBOUGHT` | `60` | RSI value (≥) considered overbought on the confluency timeframe |
| `CONFLUENCY_OVERSOLD` | `40` | RSI value (≤) considered oversold on the confluency timeframe |
| `EXTRA_TIMEFRAMES` | `["15m", "30m", "1D"]` | Additional timeframes shown for context only — set to `[]` to disable |
| `CANDLE_LIMIT` | `100` | Number of historical candles fetched per RSI calculation |
| `REQUEST_DELAY` | `0.05` | Delay (in seconds) added per completed request, to ease API load |
| `MAX_WORKERS` | `10` | Number of concurrent threads used to fetch market data |
| `SCAN_INTERVAL_SECONDS` | `60` | Seconds to wait between automatic scans |

Valid timeframe values for `PRIMARY_TIMEFRAME`, `CONFLUENCY_TIMEFRAME`, and entries in `EXTRA_TIMEFRAMES` are: `"15m"`, `"30m"`, `"1H"`, `"4H"`, `"1D"`.

> At least one of `SCAN_USDT_M` / `SCAN_USDC_M` must be set to `True`, or the scanner will report a configuration error and stop.

---

## Understanding the Output

Each scan prints three stages:

1. **`[1/3]`** — Fetches the list of tradable futures symbols and their 24h volume for each enabled market.
2. **`[2/3]`** — Calculates RSI across all configured timeframes for every symbol, with a live progress bar showing pairs scanned and matches found so far.
3. **`[3/3]`** — Displays the top 25 matching assets by volume, in a formatted table, followed by the same data as a JSON array.

**Table columns:**

| Column | Meaning |
|---|---|
| `#` | Rank by 24h volume among matches |
| `Symbol` | Futures trading pair (e.g. `BTCUSDT`) |
| `Market` | `USDT-FUTURES` or `USDC-FUTURES` |
| `Signal` | `[H] OVERBOUGHT` or `[L] OVERSOLD` |
| Timeframe columns | RSI value for each configured timeframe |
| `Volume (USDT)` | 24-hour trading volume |
| `Price` | Last traded price |
| `24h Chg %` | 24-hour price change percentage |

The **JSON block** at the end of every scan mirrors the table data in machine-readable form, useful if you want to pipe the output into another script, log file, or alerting tool.

A **sound alert** plays automatically at the end of any scan that finds one or more matches.

---

## Stopping the Scanner

Press **`Ctrl + C`** at any time. The script will catch the interrupt, print a summary of how many scans were completed, and exit cleanly.

---

## Troubleshooting

**"No matches found" every scan**
This is normal — it simply means no assets currently meet your configured RSI thresholds on both timeframes. Try loosening the thresholds (e.g. `PRIMARY_OVERBOUGHT = 65`) or wait for market conditions to shift.

**`[FAIL] ERROR: Could not fetch symbols from Bitget API`**
Usually means a network issue or a temporary Bitget API outage. Check your internet connection and try again; if it persists, check [Bitget's status page](https://www.bitget.com) or try again later.

**`[FAIL] No markets enabled!`**
Set `SCAN_USDT_M` and/or `SCAN_USDC_M` to `True` in the configuration section.

**`python3: command not found` (macOS/Linux) or `'python' is not recognized` (Windows)**
Python isn't installed or isn't on your system `PATH`. Revisit the [Installation](#installation) steps for your OS — on Windows, re-run the installer and ensure "Add Python to PATH" is checked.

**No sound plays on alert**
- macOS: `afplay` is built in and should always work.
- Windows: `winsound` is built into Python on Windows and should always work.
- Linux: requires `paplay` (from `pulseaudio-utils`/`libpulse`). If it's missing, the script falls back to a terminal bell character, which may be silent depending on your terminal's bell settings.

**Scan feels slow, or many symbols return no RSI data**
Try lowering `MAX_WORKERS` or increasing `REQUEST_DELAY` slightly — this reduces concurrent load and can help if requests are being rate-limited or timing out.

---

## Disclaimer

This script is provided for **informational and educational purposes only**. RSI is a lagging technical indicator and does not predict future price movement. Nothing in this tool's output constitutes financial, investment, or trading advice. Futures trading carries substantial risk, including the potential loss of more than your initial investment. Always do your own research and consider consulting a licensed financial professional before making trading decisions.
