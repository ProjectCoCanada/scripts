#!/usr/bin/env python3
"""
AGT Bitget Futures RSI Scanner
Scans for top 25 assets by volume with extreme RSI on a configurable
primary timeframe, confirmed by a configurable confluency timeframe.

Auto-runs every 300 seconds (5 minutes) and plays a sound if results exist.

Usage: python3 RSIc.py
"""

import urllib.request
import urllib.parse
import json
import time
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# --- Market toggles ---
SCAN_USDT_M = False   # Set to True to scan USDT-Margined futures
SCAN_USDC_M = True   # Set to True to scan USDC-Margined futures

# --- Primary trigger timeframe ---
# This is the timeframe that must hit extreme RSI for an asset to be flagged.
# Valid options: "15m", "30m", "1H", "4H", "1D"
PRIMARY_TIMEFRAME = "1H"
PRIMARY_OVERBOUGHT = 70
PRIMARY_OVERSOLD = 30

# --- Confluency timeframe ---
# This timeframe must also align with the primary signal for confirmation.
# Valid options: "15m", "30m", "1H", "4H", "1D"
CONFLUENCY_TIMEFRAME = "4H"
CONFLUENCY_OVERBOUGHT = 60
CONFLUENCY_OVERSOLD = 40

# --- Additional display timeframes ---
# These are fetched and shown for context but do NOT affect filtering.
# Set to empty list [] to disable extra timeframes.
EXTRA_TIMEFRAMES = ["15m", "30m", "1D"]

# --- Scan settings ---
CANDLE_LIMIT = 100
REQUEST_DELAY = 0.05
MAX_WORKERS = 10
SCAN_INTERVAL_SECONDS = 60

# ═══════════════════════════════════════════════════════════════════════════
# INTERNAL CONFIG
# ═══════════════════════════════════════════════════════════════════════════

BASE_URL = "https://api.bitget.com"

PRODUCT_TYPES = []
if SCAN_USDT_M:
    PRODUCT_TYPES.append("USDT-FUTURES")
if SCAN_USDC_M:
    PRODUCT_TYPES.append("USDC-FUTURES")

# Validate timeframe config
VALID_TIMEFRAMES = ["15m", "30m", "1H", "4H", "1D"]

# ═══════════════════════════════════════════════════════════════════════════
# Sound Helpers
# ═══════════════════════════════════════════════════════════════════════════

def play_alert():
    """Play a system alert sound. Tries multiple methods for cross-platform support."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
        elif sys.platform.startswith("linux"):
            subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"], check=False)
        elif sys.platform == "win32":
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        print("\a", end="", flush=True)


# ═══════════════════════════════════════════════════════════════════════════
# Visual Progress Helpers
# ═══════════════════════════════════════════════════════════════════════════

class Spinner:
    chars = ['|', '/', '-', '\\']
    def __init__(self):
        self.idx = 0
    def next(self):
        c = self.chars[self.idx % len(self.chars)]
        self.idx += 1
        return c

spinner = Spinner()

def print_progress(message, current, total, matched=0, end=False):
    pct = (current / total * 100) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = '#' * filled + '-' * (bar_len - filled)

    if end:
        line = "  [OK] " + message
    else:
        spin = spinner.next()
        line = "  [" + spin + "] " + message + " [" + bar + "] " + str(current) + "/" + str(total) + " (" + str(round(pct, 1)) + "%) | Matched: " + str(matched)

    sys.stdout.write("\r" + line)
    if end:
        sys.stdout.write("\n")
    sys.stdout.flush()


def clear_line():
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════════════════
# API Helpers
# ═══════════════════════════════════════════════════════════════════════════

def fetch_json(path, params=None):
    url = BASE_URL + path
    if params:
        query = urllib.parse.urlencode(params)
        url = url + "?" + query

    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (entries.py)"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") != "00000":
                return None
            return data.get("data", [])
    except Exception:
        return None


def get_futures_symbols(product_type):
    data = fetch_json("/api/v2/mix/market/tickers", {"productType": product_type})
    if not data:
        return []

    symbols = []
    for item in data:
        symbol = item.get("symbol")
        volume = float(item.get("usdtVolume", 0) or item.get("quoteVolume", 0) or 0)
        if symbol and volume > 0:
            symbols.append({
                "symbol": symbol,
                "product_type": product_type,
                "volume": volume,
                "price": float(item.get("lastPr", 0)),
                "change_24h": float(item.get("change24h", 0)),
            })

    symbols.sort(key=lambda x: x["volume"], reverse=True)
    return symbols


def get_candles(symbol, product_type, granularity, limit=CANDLE_LIMIT):
    return fetch_json("/api/v2/mix/market/candles", {
        "symbol": symbol,
        "productType": product_type,
        "granularity": granularity,
        "limit": str(limit),
    })


def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def get_rsi_for_timeframe(symbol_info, granularity):
    """Calculate RSI for a single timeframe. Returns rsi value or None."""
    candles = get_candles(symbol_info["symbol"], symbol_info["product_type"], granularity)
    if not candles or len(candles) < 20:
        return None

    closes = [float(c[4]) for c in candles]
    return calculate_rsi(closes)


def analyze_symbol(symbol_info):
    symbol = symbol_info["symbol"]
    product_type = symbol_info["product_type"]

    # Primary timeframe check
    primary_rsi = get_rsi_for_timeframe(symbol_info, PRIMARY_TIMEFRAME)
    if primary_rsi is None:
        return None

    is_overbought_primary = primary_rsi >= PRIMARY_OVERBOUGHT
    is_oversold_primary = primary_rsi <= PRIMARY_OVERSOLD

    if not (is_overbought_primary or is_oversold_primary):
        return None

    # Confluency timeframe check
    confluency_rsi = get_rsi_for_timeframe(symbol_info, CONFLUENCY_TIMEFRAME)
    if confluency_rsi is None:
        return None

    is_overbought_confluency = confluency_rsi >= CONFLUENCY_OVERBOUGHT
    is_oversold_confluency = confluency_rsi <= CONFLUENCY_OVERSOLD

    if is_overbought_primary and is_overbought_confluency:
        signal = "OVERBOUGHT"
    elif is_oversold_primary and is_oversold_confluency:
        signal = "OVERSOLD"
    else:
        return None

    # Extra timeframes for display
    extra_rsis = {}
    for tf in EXTRA_TIMEFRAMES:
        extra_rsis[tf] = get_rsi_for_timeframe(symbol_info, tf)

    result = {
        "symbol": symbol,
        "product_type": product_type,
        "volume": symbol_info["volume"],
        "price": symbol_info["price"],
        "change_24h": symbol_info["change_24h"],
        "signal": signal,
        "rsi_" + PRIMARY_TIMEFRAME.lower(): primary_rsi,
        "rsi_" + CONFLUENCY_TIMEFRAME.lower(): confluency_rsi,
    }

    for tf, rsi in extra_rsis.items():
        result["rsi_" + tf.lower()] = rsi

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Single Scan
# ═══════════════════════════════════════════════════════════════════════════

def run_scan(scan_number=1):
    print()
    print("+" + "-" * 68 + "+")
    print("|" + " " * 15 + "AGT BITGET FUTURES RSI SCANNER" + " " * 27 + "|")
    print("|" + " " * 4 + "Primary: " + PRIMARY_TIMEFRAME + " RSI >=" + str(PRIMARY_OVERBOUGHT) + " / <=" + str(PRIMARY_OVERSOLD) + "  |  Confluency: " + CONFLUENCY_TIMEFRAME + " RSI >=" + str(CONFLUENCY_OVERBOUGHT) + " / <=" + str(CONFLUENCY_OVERSOLD) + " " * 4 + "|")
    print("|" + " " * 20 + "Scan #" + str(scan_number) + " " * (42 - len(str(scan_number))) + "|")
    print("+" + "-" * 68 + "+")
    print()

    # Validate config
    if not PRODUCT_TYPES:
        print("  [FAIL] No markets enabled! Set SCAN_USDT_M and/or SCAN_USDC_M to True.")
        return None

    if PRIMARY_TIMEFRAME not in VALID_TIMEFRAMES:
        print("  [FAIL] Invalid PRIMARY_TIMEFRAME: " + PRIMARY_TIMEFRAME)
        print("  Valid options: " + ", ".join(VALID_TIMEFRAMES))
        return None

    if CONFLUENCY_TIMEFRAME not in VALID_TIMEFRAMES:
        print("  [FAIL] Invalid CONFLUENCY_TIMEFRAME: " + CONFLUENCY_TIMEFRAME)
        print("  Valid options: " + ", ".join(VALID_TIMEFRAMES))
        return None

    for tf in EXTRA_TIMEFRAMES:
        if tf not in VALID_TIMEFRAMES:
            print("  [FAIL] Invalid timeframe in EXTRA_TIMEFRAMES: " + tf)
            print("  Valid options: " + ", ".join(VALID_TIMEFRAMES))
            return None

    active_markets = ", ".join(PRODUCT_TYPES)
    print("  Active markets: " + active_markets)
    print("  Primary trigger: " + PRIMARY_TIMEFRAME + " | Confluency: " + CONFLUENCY_TIMEFRAME)
    if EXTRA_TIMEFRAMES:
        print("  Extra timeframes: " + ", ".join(EXTRA_TIMEFRAMES))
    print()

    # Step 1: Fetch symbols from all enabled markets
    print("[1/3] Fetching futures symbols and 24h volumes...")
    all_symbols = []
    for pt in PRODUCT_TYPES:
        symbols = get_futures_symbols(pt)
        all_symbols.extend(symbols)
        print("  [OK] " + pt + ": " + str(len(symbols)) + " pairs.")

    if not all_symbols:
        print("  [FAIL] ERROR: Could not fetch symbols from Bitget API.")
        return None

    all_symbols.sort(key=lambda x: x["volume"], reverse=True)
    print("  [OK] Total: " + str(len(all_symbols)) + " pairs across all enabled markets.")
    print()

    # Step 2: Scan RSI
    all_tfs = [PRIMARY_TIMEFRAME, CONFLUENCY_TIMEFRAME] + EXTRA_TIMEFRAMES
    print("[2/3] Scanning RSI across all symbols...")
    print("      (Fetching " + ", ".join(all_tfs) + " candle data for each pair)")
    print()

    results = []
    total = len(all_symbols)
    matched_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(analyze_symbol, s): s for s in all_symbols}
        completed = 0

        for future in as_completed(futures):
            completed += 1
            result = future.result()
            if result:
                matched_count += 1
                results.append(result)

            print_progress(
                "Scanning symbols",
                completed,
                total,
                matched=matched_count
            )
            time.sleep(REQUEST_DELAY)

    clear_line()
    print_progress("Scan complete", total, total, matched=matched_count, end=True)
    print("      " + str(matched_count) + " asset(s) matched the RSI criteria.")
    print()

    if not results:
        print("+" + "-" * 68 + "+")
        print("|" + " " * 20 + "NO MATCHES FOUND" + " " * 32 + "|")
        print("|" + " " * 8 + "No assets currently meet the RSI criteria." + " " * 18 + "|")
        print("+" + "-" * 68 + "+")
        print()
        return []

    # Step 3: Display results
    results.sort(key=lambda x: x["volume"], reverse=True)
    top_25 = results[:25]

    print("[3/3] Top 25 Assets by 24h Volume:")
    print()

    # Build dynamic header based on configured timeframes
    tf_cols = ""
    for tf in all_tfs:
        tf_cols = tf_cols + tf.ljust(7) + " "

    header = (
        "#".ljust(4) + " " + "Symbol".ljust(20) + " " + "Market".ljust(14) + " " +
        "Signal".ljust(12) + " " + tf_cols +
        "Volume (USDT)".ljust(18) + " " + "Price".ljust(14) + " " + "24h Chg %".ljust(10)
    )
    sep = "-" * len(header)

    print(sep)
    print(header)
    print(sep)

    for i, r in enumerate(top_25, 1):
        signal_icon = "[H]" if r["signal"] == "OVERBOUGHT" else "[L]"

        tf_values = ""
        for tf in all_tfs:
            key = "rsi_" + tf.lower()
            val = r.get(key)
            val_str = str(val) if val is not None else "N/A"
            tf_values = tf_values + val_str.ljust(7) + " "

        print(
            str(i).ljust(4) + " " +
            r["symbol"].ljust(20) + " " +
            r["product_type"].ljust(14) + " " +
            signal_icon + " " + r["signal"].ljust(8) + " " +
            tf_values +
            ("{:,.0f}".format(r["volume"])).rjust(17) + " " +
            ("{:,.4f}".format(r["price"])).rjust(13) + " " +
            ("{:.2f}%".format(r["change_24h"])).rjust(9)
        )

    print(sep)
    print()

    overbought = [r for r in top_25 if r["signal"] == "OVERBOUGHT"]
    oversold = [r for r in top_25 if r["signal"] == "OVERSOLD"]

    print("Summary:")
    print("  [H] Overbought (" + PRIMARY_TIMEFRAME + " >=" + str(PRIMARY_OVERBOUGHT) + ", " + CONFLUENCY_TIMEFRAME + " >=" + str(CONFLUENCY_OVERBOUGHT) + "): " + str(len(overbought)) + " assets")
    print("  [L] Oversold   (" + PRIMARY_TIMEFRAME + " <=" + str(PRIMARY_OVERSOLD) + ", " + CONFLUENCY_TIMEFRAME + " <=" + str(CONFLUENCY_OVERSOLD) + "): " + str(len(oversold)) + " assets")
    print()

    print("-" * 40)
    print("JSON Output (pipe-friendly):")
    print("-" * 40)
    print(json.dumps(top_25, indent=2))
    print()

    return top_25


# ═══════════════════════════════════════════════════════════════════════════
# Main Loop
# ═══════════════════════════════════════════════════════════════════════════

def main():
    scan_count = 0

    print()
    print("=" * 70)
    print("  AGT BITGET FUTURES RSI SCANNER - AUTO MODE")
    print("  Primary: " + PRIMARY_TIMEFRAME + " | Confluency: " + CONFLUENCY_TIMEFRAME)
    print("  Scanning every " + str(SCAN_INTERVAL_SECONDS) + " seconds")
    print("  Press Ctrl+C to stop")
    print("=" * 70)
    print()

    try:
        while True:
            scan_count += 1
            results = run_scan(scan_count)

            if results is None:
                print("  Configuration error. Fix settings and restart.")
                break

            if results and len(results) > 0:
                print("!!! ALERT: " + str(len(results)) + " asset(s) found matching criteria !!!")
                play_alert()
            else:
                print("No matching assets this scan.")

            print()
            print("-" * 70)
            print("  Next scan in " + str(SCAN_INTERVAL_SECONDS) + " seconds...")
            print("  (Press Ctrl+C to exit)")
            print("-" * 70)
            print()

            time.sleep(SCAN_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print()
        print()
        print("=" * 70)
        print("  Scanner stopped by user.")
        print("  Total scans completed: " + str(scan_count))
        print("=" * 70)
        print()


if __name__ == "__main__":
    main()
