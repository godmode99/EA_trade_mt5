"""Fetch OHLCV candles from MetaTrader 5 and export them to CSV files.

The module exposes a small command line utility that connects to a running
MetaTrader 5 terminal, retrieves historical candles for the requested symbol
and timeframe, and writes them to disk.  The implementation is intentionally
simple so that it can be reused in notebooks or automated scripts.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Mapping, Optional

from zoneinfo import ZoneInfo

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


def ensure_mt5_initialized() -> None:
    """Initialise the MetaTrader 5 terminal if it is not already connected."""

    if mt5.initialize():
        return

    code, message = mt5.last_error()
    raise RuntimeError(f"Failed to initialise MetaTrader 5: {code} - {message}")


def resolve_timeframe(timeframe: str) -> int:
    """Return the MetaTrader 5 constant corresponding to ``timeframe``."""

    try:
        return TIMEFRAME_ALIASES[timeframe.upper()]
    except KeyError as exc:  # pragma: no cover - trivial branch
        raise ValueError(f"Unsupported timeframe: {timeframe}") from exc


def fetch_ohlcv(symbol: str, timeframe: str, bars: int) -> List[mt5.Rates]:
    """Retrieve OHLCV candles from MetaTrader 5.

    Parameters
    ----------
    symbol:
        Trading symbol, e.g. ``"EURUSD"``.
    timeframe:
        Timeframe string such as ``"M1"`` or ``"H1"``.
    bars:
        Maximum number of candles to return.  Candles are ordered from oldest to
        newest as returned by :func:`MetaTrader5.copy_rates_from_pos`.
    """

    ensure_mt5_initialized()
    tf_constant = resolve_timeframe(timeframe)
    rates = mt5.copy_rates_from_pos(symbol, tf_constant, 0, bars)
    if rates is None:
        code, message = mt5.last_error()
        raise RuntimeError(f"Failed to fetch rates: {code} - {message}")

    return list(rates)


def format_timestamp(timestamp: float, tz_name: str) -> str:
    """Convert an MT5 epoch timestamp to an ISO formatted string."""

    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    if tz_name.upper() == "UTC":
        target_dt = dt
    else:
        target_dt = dt.astimezone(ZoneInfo(tz_name))
    return target_dt.isoformat()


def export_to_csv(rates: Iterable[mt5.Rates], output_path: Path, tz_name: str) -> None:
    """Write OHLCV records to ``output_path`` in CSV format."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
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
        for rate in rates:
            writer.writerow(
                [
                    format_timestamp(rate["time"], tz_name),
                    rate["open"],
                    rate["high"],
                    rate["low"],
                    rate["close"],
                    rate["tick_volume"],
                    rate["spread"],
                    rate["real_volume"],
                ]
            )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch OHLCV data from MetaTrader 5 and save it as a CSV file."
    )
    parser.add_argument("symbol", help="Trading symbol, e.g. EURUSD")
    parser.add_argument(
        "--timeframe",
        default="M1",
        help="Timeframe code such as M1, H1, D1",
    )
    parser.add_argument(
        "--bars",
        type=int,
        default=100,
        help="Number of recent candles to export",
    )
    parser.add_argument(
        "--timezone",
        default="UTC",
        help="IANA timezone name used when writing timestamps",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/ohlcv.csv"),
        help="Destination CSV file",
    )
    return parser


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = build_arg_parser()
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    rates = fetch_ohlcv(args.symbol, args.timeframe, args.bars)
    export_to_csv(rates, args.output, args.timezone)
    print(f"Saved {len(rates)} candles for {args.symbol} {args.timeframe} -> {args.output}")
    mt5.shutdown()


if __name__ == "__main__":
    main()
