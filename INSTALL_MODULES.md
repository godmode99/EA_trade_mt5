# วิธีติดตั้งโมดูลที่จำเป็นสำหรับ `fetch_ohlcv.py`

สคริปต์ `fetch_ohlcv.py` ต้องใช้ไลบรารีภายนอกเพื่อเชื่อมต่อกับ MetaTrader 5 และจัดการข้อมูลตารางเวลา ดังนั้นจึงควรเตรียมสภาพแวดล้อม Python ให้พร้อมก่อนรันคำสั่ง `py fetch_ohlcv.py` หรือ `python fetch_ohlcv.py`.

## 1. เตรียม Virtual Environment (แนะนำ)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

> หากใช้ macOS/Linux ให้ปรับคำสั่ง activate เป็น `source .venv/bin/activate`.

## 2. อัปเดต `pip`

```powershell
python -m pip install --upgrade pip
```

## 3. ติดตั้งโมดูลหลักที่ต้องใช้

> เพื่อให้แน่ใจว่าการติดตั้งอยู่ภายใน virtual environment เดียวกัน แนะนำให้เรียก `pip` ผ่าน `python -m pip` เสมอ (ป้องกันไม่ให้ไปใช้ `pip` นอก venv โดยไม่ตั้งใจ)

```powershell
python -m pip install pandas MetaTrader5
```

## 4. ติดตั้งโมดูลเสริม (สำหรับ Python < 3.9)

สคริปต์รองรับทั้ง `zoneinfo` (มีใน Python 3.9 ขึ้นไป) และ `pytz` เป็นทางเลือกสำรอง หากใช้ Python รุ่นเก่ากว่าให้ติดตั้ง `pytz` เพิ่มเติม:

```powershell
python -m pip install pytz
```

## 5. ตรวจสอบการติดตั้ง

หลังจากติดตั้งโมดูลแล้ว สามารถรันสคริปต์ได้ด้วย:

```powershell
python fetch_ohlcv.py
```

หากไม่มีข้อความแจ้ง error เรื่อง `ModuleNotFoundError` อีก แสดงว่าการติดตั้งโมดูลเรียบร้อยแล้ว

## 6. ทางเลือก: ใช้ไฟล์ `requirements.txt`

หากต้องการติดตั้งรวดเดียว สามารถสร้างไฟล์ `requirements.txt` ที่มีเนื้อหา:

```
pandas
MetaTrader5
pytz ; python_version < "3.9"
```

แล้วรันคำสั่ง

```powershell
python -m pip install -r requirements.txt
```

เพื่อให้ง่ายต่อการติดตั้งซ้ำในอนาคต
