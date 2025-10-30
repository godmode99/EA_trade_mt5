# -*- coding: utf-8 -*-
"""
MT5 OHLCV Fetcher & Bar-Close Watcher
ครบตามโจทย์:
1) ฟังก์ชัน fetch OHLCV จาก MT5
2) export CSV
3) กำหนด timeframe ได้
4) กำหนดจำนวนแท่งเทียนได้
5) กำหนดชื่อไฟล์ CSV ได้
6) กำหนดสัญลักษณ์ (คู่เงิน/สัญลักษณ์) ได้
7) แปลงเวลาไปยัง timezone อื่นได้
8) มี watcher คอยดึงเมื่อแท่งปิดในแต่ละ timeframe
"""

import os
import time
from datetime import datetime, timezone, timedelta

try:
    import pandas as pd
except ModuleNotFoundError as exc:
    # ผู้ใช้บางรายอาจติดตั้ง pandas แล้ว แต่ขาด dependency ภายในอย่าง "six"
    # จึงแสดงคำแนะนำที่ชัดเจนเพื่อแก้ไข
    if exc.name == "six":
        raise SystemExit(
            "ไม่พบโมดูล 'six' ซึ่งเป็น dependency ของ pandas\n"
            "โปรดติดตั้งด้วยคำสั่ง: python -m pip install six"
        ) from exc
    raise
try:
    # ถ้ามี Python 3.9+ ใช้ zoneinfo (แนะนำ ความแม่นยำสูงกว่า pytz ในอนาคต)
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except Exception:
    import pytz
    HAS_ZONEINFO = False

import MetaTrader5 as mt5


# -----------------------------
# Utils: Timeframe mapping
# -----------------------------
def timeframe_to_mt5(tf: str):
    """รับ string/รหัส timeframe แล้วแมปเป็น MT5 timeframe constant"""
    tf = str(tf).strip().upper()
    MAP = {
        "M1": mt5.TIMEFRAME_M1, "1M": mt5.TIMEFRAME_M1,
        "M2": mt5.TIMEFRAME_M2, "2M": mt5.TIMEFRAME_M2,
        "M3": mt5.TIMEFRAME_M3, "3M": mt5.TIMEFRAME_M3,
        "M4": mt5.TIMEFRAME_M4, "4M": mt5.TIMEFRAME_M4,
        "M5": mt5.TIMEFRAME_M5, "5M": mt5.TIMEFRAME_M5,
        "M10": mt5.TIMEFRAME_M10, "10M": mt5.TIMEFRAME_M10,
        "M15": mt5.TIMEFRAME_M15, "15M": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30, "30M": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "1H": mt5.TIMEFRAME_H1, "60M": mt5.TIMEFRAME_H1,
        "H2": mt5.TIMEFRAME_H2, "2H": mt5.TIMEFRAME_H2,
        "H3": mt5.TIMEFRAME_H3, "3H": mt5.TIMEFRAME_H3,
        "H4": mt5.TIMEFRAME_H4, "4H": mt5.TIMEFRAME_H4,
        "H6": mt5.TIMEFRAME_H6, "6H": mt5.TIMEFRAME_H6,
        "H8": mt5.TIMEFRAME_H8, "8H": mt5.TIMEFRAME_H8,
        "H12": mt5.TIMEFRAME_H12, "12H": mt5.TIMEFRAME_H12,
        "D1": mt5.TIMEFRAME_D1, "1D": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1, "1W": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1, "1MN": mt5.TIMEFRAME_MN1,
    }
    if tf not in MAP:
        raise ValueError(f"ไม่รู้จัก timeframe: {tf}")
    return MAP[tf]


def timeframe_seconds(tf: str) -> int:
    """ระยะเวลา 1 แท่ง (วินาที) เพื่อคำนวณเวลาปิดแท่ง"""
    tf = str(tf).strip().upper()
    BASE = {
        "M1": 60, "M2": 120, "M3": 180, "M4": 240, "M5": 300, "M10": 600, "M15": 900, "M30": 1800,
        "H1": 3600, "H2": 7200, "H3": 10800, "H4": 14400, "H6": 21600, "H8": 28800, "H12": 43200,
        "D1": 86400, "W1": 604800,
        # MN1: ใช้คร่าว ๆ 30 วัน (ตลาดจริงจะขึ้นกับปฏิทิน) — สำหรับ watcher ให้หลีกเลี่ยง MN1
        "MN1": 2592000
    }
    if tf not in BASE:
        raise ValueError(f"ไม่รู้จัก timeframe: {tf}")
    return BASE[tf]


# -----------------------------
# Init / Connect MT5
# -----------------------------
def init_mt5():
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize ล้มเหลว: {mt5.last_error()}")
    return True


def shutdown_mt5():
    try:
        mt5.shutdown()
    except Exception:
        pass


# -----------------------------
# Timezone helper
# -----------------------------
def to_tz(dt_utc: datetime, tz_name: str) -> datetime:
    """รับ datetime แบบ UTC -> แปลงเป็น timezone ปลายทาง"""
    if HAS_ZONEINFO:
        return dt_utc.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(tz_name))
    else:
        return dt_utc.replace(tzinfo=timezone.utc).astimezone(pytz.timezone(tz_name))


# -----------------------------
# 1) ฟังก์ชัน fetch OHLCV จาก MT5
# -----------------------------
def fetch_ohlcv_mt5(
    symbol: str,
    timeframe: str = "M15",
    bars: int = 500,
    tz_out: str = "UTC",
) -> pd.DataFrame:
    """
    ดึง OHLCV ตามสัญลักษณ์/TF/จำนวนแท่ง แล้วคืน DataFrame
    - time จะถูกแปลงเป็น tz_out
    """
    tf_const = timeframe_to_mt5(timeframe)

    # เลือก symbol
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"เลือกสัญลักษณ์ไม่สำเร็จ: {symbol}")

    # ดึงข้อมูล: เอา 'bars' แท่งล่าสุด
    rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, bars)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"ไม่พบข้อมูล {symbol} TF={timeframe}")

    df = pd.DataFrame(rates)
    # time จาก MT5 เป็น epoch seconds (UTC)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    # แปลง timezone
    if tz_out and tz_out.upper() != "UTC":
        if HAS_ZONEINFO:
            df["time"] = df["time"].dt.tz_convert(ZoneInfo(tz_out))
        else:
            df["time"] = df["time"].dt.tz_convert(tz_out)

    # ตั้งชื่อคอลัมน์ให้ชัด (OHLCV)
    df.rename(
        columns={
            "time": "time",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "tick_volume": "tick_volume",
            "real_volume": "real_volume",
            "spread": "spread",
        },
        inplace=True,
    )

    return df[["time", "open", "high", "low", "close", "tick_volume", "real_volume", "spread"]]


# -----------------------------
# 2) export CSV (ยืดหยุ่นชื่อไฟล์/append)
# -----------------------------
def export_csv(df: pd.DataFrame, filepath: str, append: bool = False):
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    # ถ้า append แต่ไฟล์ยังไม่มี ต้องเขียน header ให้ครบ
    if append and not os.path.exists(filepath):
        append = False

    if append:
        df.to_csv(filepath, mode="a", header=False, index=False)
    else:
        df.to_csv(filepath, index=False)


# -----------------------------
# 3-7) ฟังก์ชัน main ใช้งานครั้งเดียว (fetch แล้วเซฟ)
# -----------------------------
def fetch_to_csv(
    symbol: str,
    timeframe: str,
    bars: int,
    csv_path: str,
    tz_out: str = "UTC",
    append: bool = False,
):
    init_mt5()
    try:
        df = fetch_ohlcv_mt5(symbol=symbol, timeframe=timeframe, bars=bars, tz_out=tz_out)
        export_csv(df, csv_path, append=append)
        return df
    finally:
        shutdown_mt5()


# -----------------------------
# Watcher: ยิงตอนแท่งปิด (หลาย TF ก็ได้)
# -----------------------------
def watch_and_export_on_close(
    symbol: str,
    timeframes: list,
    bars_to_keep: int = 200,
    out_dir: str = "data",
    filename_template: str = "{symbol}_{timeframe}.csv",
    tz_out: str = "UTC",
    poll_sec: float = 0.5,
    full_refresh_on_close: bool = False,
):
    """
    เฝ้ารอจนแท่ง "ปิด" ในแต่ละ timeframe แล้วค่อย export CSV
    - ถ้า full_refresh_on_close=True จะดึงทั้งก้อน (bars_to_keep แท่ง) แล้วเขียนทับไฟล์
    - ถ้า False (แนะนำ) จะดึงเฉพาะ "แท่งปิดล่าสุด" แล้ว append ลงไฟล์ (ใช้แรงน้อย)
    """
    init_mt5()
    try:
        # เตรียมไฟล์
        out_paths = {}
        for tf in timeframes:
            fname = filename_template.format(symbol=symbol, timeframe=tf)
            out_paths[tf] = os.path.join(out_dir, fname)
            os.makedirs(os.path.dirname(out_paths[tf]) or ".", exist_ok=True)
            # ถ้าไฟล์ยังไม่เคยมี เขียน header ไว้ก่อน (ดึงล่าสุดมาทั้ง block)
            if not os.path.exists(out_paths[tf]):
                df0 = fetch_ohlcv_mt5(symbol, tf, bars_to_keep, tz_out)
                export_csv(df0, out_paths[tf], append=False)

        # เก็บ state: เวลาแท่งปิดล่าสุดของแต่ละ TF
        last_closed_time = {}

        # seed เริ่มต้น
        for tf in timeframes:
            df = fetch_ohlcv_mt5(symbol, tf, 2, tz_out="UTC")  # ใช้ UTC ภายในเพื่อเปรียบเทียบเวลา
            # บรรทัด [-1] คือแท่งล่าสุด "ปิดแล้ว" จาก MT5 (copy_rates_from_pos คืนแท่งที่ปิดแล้ว)
            last_closed_time[tf] = df["time"].iloc[-1].to_pydatetime().astimezone(timezone.utc)

        print(f"เริ่มเฝ้า {symbol} TF={timeframes} | กด Ctrl+C เพื่อหยุด")

        while True:
            for tf in timeframes:
                tf_const = timeframe_to_mt5(tf)
                # ขอ 2 แท่งล่าสุดแบบ UTC เพื่อเช็คว่ามีแท่งใหม่ปิดหรือยัง
                rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, 2)
                if rates is None or len(rates) < 2:
                    continue

                # แท่งปิดล่าสุดจาก MT5 (UTC epoch)
                latest_closed_utc = datetime.fromtimestamp(int(rates[-1]["time"]), tz=timezone.utc)

                if latest_closed_utc > last_closed_time[tf]:
                    # มีแท่งใหม่ปิดแล้ว
                    if full_refresh_on_close:
                        # ดึงทั้ง block แล้วเขียนทับ
                        df = fetch_ohlcv_mt5(symbol, tf, bars_to_keep, tz_out)
                        export_csv(df, out_paths[tf], append=False)
                        print(f"[{datetime.now()}] {symbol} {tf} CLOSED -> refresh file")
                    else:
                        # append เฉพาะแท่งล่าสุด
                        row = pd.DataFrame([rates[-1]])
                        row["time"] = pd.to_datetime(row["time"], unit="s", utc=True)
                        # แปลง TZ ก่อนเขียน
                        if tz_out and tz_out.upper() != "UTC":
                            if HAS_ZONEINFO:
                                row["time"] = row["time"].dt.tz_convert(ZoneInfo(tz_out))
                            else:
                                row["time"] = row["time"].dt.tz_convert(tz_out)

                        row = row.rename(
                            columns={
                                "time": "time",
                                "open": "open",
                                "high": "high",
                                "low": "low",
                                "close": "close",
                                "tick_volume": "tick_volume",
                                "real_volume": "real_volume",
                                "spread": "spread",
                            }
                        )
                        row = row[["time", "open", "high", "low", "close", "tick_volume", "real_volume", "spread"]]
                        export_csv(row, out_paths[tf], append=True)
                        print(f"[{datetime.now()}] {symbol} {tf} CLOSED -> append last bar")

                    last_closed_time[tf] = latest_closed_utc

            time.sleep(poll_sec)

    except KeyboardInterrupt:
        print("หยุด watcher แล้ว")
    finally:
        shutdown_mt5()
