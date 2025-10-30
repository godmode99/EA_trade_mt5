# Installation Guide for Required Python Modules

สคริปต์ `fetch_ohlcv.py` ต้องใช้โมดูลภายนอกหลายตัว หากต้องการติดตั้งโมดูลเหล่านี้แบบ global (โดยไม่สร้าง `.venv`)
สามารถทำตามขั้นตอนด้านล่างได้เลย ตัวอย่างนี้อ้างอิงจาก Windows ที่ใช้ PowerShell
เหมือนกับตัวอย่างคำสั่งที่ระบุไว้ในคำถาม

## 1. ตรวจสอบเวอร์ชัน Python และ pip
```powershell
python --version
python -m pip --version
```
หากคำสั่ง `python` ไม่ทำงาน ให้ลองใช้ `py` แทน (เช่น `py --version`).

## 2. อัปเกรด pip (แนะนำ)
```powershell
python -m pip install --upgrade pip
```

## 3. ติดตั้งโมดูลที่จำเป็น
รันคำสั่งต่อไปนี้เพื่อให้ได้ทุกโมดูลที่ `fetch_ohlcv.py` ใช้งาน (รวมถึง dependency ภายในอย่าง `six`):
```powershell
python -m pip install -r requirements.txt
```
> **หมายเหตุ**
> * หากติดตั้งแบบกำหนดเอง ควรแน่ใจว่ามีแพ็กเกจ `pandas`, `MetaTrader5`, `python-dateutil`, `pytz` และ `six` ครบถ้วน
> * บน Python 3.9 ขึ้นไป สามารถใช้โมดูล `zoneinfo` ที่มีมาให้ใน Python ได้อยู่แล้ว ไม่ต้องติดตั้งเพิ่ม
> * โมดูล `pytz` จะถูกใช้เฉพาะกรณีที่ไม่สามารถใช้ `zoneinfo` ได้

## 4. ทดสอบการนำเข้าโมดูล
หลังติดตั้งเสร็จ สามารถทดสอบโดยการเปิด PowerShell แล้วรัน:
```powershell
python - <<'PY'
import pandas
import MetaTrader5
import pytz
print("All modules imported successfully!")
PY
```
หากไม่พบข้อความผิดพลาด แสดงว่าพร้อมใช้งาน

## 5. รันสคริปต์
เมื่อโมดูลครบแล้ว สามารถรันสคริปต์ได้ตามปกติ:
```powershell
python fetch_ohlcv.py
```
หากยังพบข้อผิดพลาด ให้ตรวจสอบว่าเปิด MetaTrader 5 และอนุญาตการเชื่อมต่อไว้เรียบร้อยแล้ว เพราะโมดูล `MetaTrader5` ต้องเชื่อมต่อกับโปรแกรม MT5 ที่เปิดใช้งานอยู่

---
หากต้องการติดตั้งโมดูลเพิ่มในอนาคต ให้ใช้รูปแบบคำสั่ง `python -m pip install <module-name>` เช่น
```powershell
python -m pip install numpy
```
