"""Utility for fetching OHLCV data from MetaTrader 5 and exporting it to CSV files.

This module exposes a :func:`fetch_ohlcv` function and a command line interface that
can monitor multiple timeframes.  Every time a candle is completed for a timeframe,
its recent OHLCV history is refreshed and written to disk.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    from backports.zoneinfo import ZoneInfo  # type: ignore

import MetaTrader5 as mt5


TIMEFRAME_ALIASES: Mapping[str, int] = {
    "M1": mt5.TIMEFRAME_M1,
    "M2": mt5.TIMEFRAME_M2,
    "M3": mt5.TIMEFRAME_M3,
    "M4": mt5.TIMEFRAME_M4,
    "M5": mt5.TIMEFRAME_M5,
    "M6": mt5.TIMEFRAME_M6,
    "M10": mt5.TIMEFRAME_M10,
    "M12": mt5.TIMEFRAME_M12,
    "M15": mt5.TIMEFRAME_M15,
    "M20": mt5.TIMEFRAME_M20,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H2": mt5.TIMEFRAME_H2,
    "H3": mt5.TIMEFRAME_H3,
    "H4": mt5.TIMEFRAME_H4,
    "H6": mt5.TIMEFRAME_H6,
    "H8": mt5.TIMEFRAME_H8,
    "H12": mt5.TIMEFRAME_H12,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}


@dataclass
class FetchConfig:
    """Runtime configuration used by the fetcher."""

    symbol: str
    timeframes: List[str]
    bars: int
    timezone: str
    filename_template: str
    output_dir: Path
    poll_interval: float


def resolve_timeframe(timeframe: str) -> int:
    """Return the MetaTrader 5 constant that corresponds to ``timeframe``.

    Parameters
    ----------
    timeframe:
        Timeframe string such as ``"M1"`` or ``"H4"``.

    Returns
    -------
    int
        The MetaTrader 5 timeframe constant.

    Raises
    ------
    ValueError
        If ``timeframe`` is unknown.
    """

    try:
        return TIMEFRAME_ALIASES[timeframe.upper()]
    except KeyError as exc:  # pragma: no cover - trivial
        raise ValueError(f"Unsupported timeframe: {timeframe}") from exc


def ensure_mt5_initialized() -> None:
    """Initialise the MetaTrader 5 terminal if it is not already ready."""

    if mt5.initialize():
        return

    # If initialize returns ``False`` it exposes error details via ``mt5.last_error``.
    error_code, error_message = mt5.last_error()
    raise RuntimeError(
        f"Failed to initialise MetaTrader 5: {error_code} - {error_message}"
    )


def fetch_ohlcv(symbol: str, timeframe: str, bars: int) -> List[Dict[str, float]]:
    """Fetch OHLCV information for ``symbol`` and ``timeframe``.

    Parameters
    ----------
    symbol:
        Trading symbol, e.g. ``"EURUSD"``.
    timeframe:
        Timeframe string such as ``"M1"`` or ``"H1"``.
    bars:
        Maximum number of candles to fetch. The most recent candles are returned.

    Returns
    -------
    list of dict
        Each record contains ``time``, ``open``, ``high``, ``low``, ``close``,
        ``tick_volume``, ``spread`` and ``real_volume``.
    """

    ensure_mt5_initialized()
    tf_constant = resolve_timeframe(timeframe)
    rates = mt5.copy_rates_from_pos(symbol, tf_constant, 0, bars)
    if rates is None:
        error_code, error_message = mt5.last_error()
        raise RuntimeError(
            f"Failed to copy rates for {symbol} {timeframe}: {error_code} - {error_message}"
        )

    records: List[Dict[str, float]] = []
    for rate in rates:
        records.append(
            {
                "time": float(rate["time"]),
                "open": float(rate["open"]),
                "high": float(rate["high"]),
                "low": float(rate["low"]),
                "close": float(rate["close"]),
                "tick_volume": float(rate["tick_volume"]),
                "spread": float(rate["spread"]),
                "real_volume": float(rate["real_volume"]),
            }
        )
    return records


def format_time(timestamp: float, tz_name: str) -> str:
    """Convert ``timestamp`` to an ISO-8601 string in ``tz_name`` timezone."""

    dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    target_tz = ZoneInfo(tz_name)
    return dt_utc.astimezone(target_tz).isoformat()


def export_to_csv(records: Iterable[Mapping[str, float]], filepath: Path, tz_name: str) -> None:
    """Write ``records`` to ``filepath`` and include timezone-adjusted timestamps."""

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "time",
                "open",
                "high",
                "low",
                "close",
                "tick_volume",
                "spread",
                "real_volume",
            ]
        )
        for record in records:
            writer.writerow(
                [
                    format_time(record["time"], tz_name),
                    record["open"],
                    record["high"],
                    record["low"],
                    record["close"],
                    record["tick_volume"],
                    record["spread"],
                    record["real_volume"],
                ]
            )


def monitor_timeframes(config: FetchConfig) -> None:
    """Continuously refresh OHLCV CSVs whenever a candle closes."""

    last_times: Dict[str, float] = {}

    try:
        while True:
            for tf in config.timeframes:
                records = fetch_ohlcv(config.symbol, tf, config.bars)
                if not records:
                    continue

                last_record_time = records[-1]["time"]
                if last_times.get(tf) == last_record_time:
                    # No new candle yet; skip writing to avoid redundant I/O.
                    continue

                last_times[tf] = last_record_time
                filename = config.filename_template.format(symbol=config.symbol, timeframe=tf)
                export_to_csv(records, config.output_dir / filename, config.timezone)
                print(
                    f"[{datetime.now().isoformat()}] Updated {config.symbol} {tf}"
                    f" -> {filename}"
                )

            time.sleep(config.poll_interval)
    except KeyboardInterrupt:
        print("Stopped by user", file=sys.stderr)
    finally:
        mt5.shutdown()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch OHLCV data from MetaTrader 5 and export to CSV files when candles close."
        )
    )
    parser.add_argument("symbol", help="Trading symbol, e.g. EURUSD")
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=["M1"],
        help="One or more timeframe codes (e.g. M1 H1 D1)",
    )
    parser.add_argument(
        "--bars",
        type=int,
        default=100,
        help="Number of most recent candles to export",
    )
    parser.add_argument(
        "--timezone",
        default="UTC",
        help="Target timezone for the exported timestamps (IANA name)",
    )
    parser.add_argument(
        "--filename-template",
        default="{symbol}_{timeframe}.csv",
        help="Template for CSV filenames (supports {symbol} and {timeframe})",
    )
    parser.add_argument(
        "--output-dir",
        default="./data",
        type=Path,
        help="Directory where CSV files will be stored",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Seconds to wait between checks for new candles",
    )
    return parser


def parse_args(argv: Optional[Iterable[str]] = None) -> FetchConfig:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return FetchConfig(
        symbol=args.symbol,
        timeframes=[tf.upper() for tf in args.timeframes],
        bars=args.bars,
        timezone=args.timezone,
        filename_template=args.filename_template,
        output_dir=args.output_dir,
        poll_interval=args.poll_interval,
    )


def main(argv: Optional[Iterable[str]] = None) -> None:
    config = parse_args(argv)
    monitor_timeframes(config)


if __name__ == "__main__":
    main()
