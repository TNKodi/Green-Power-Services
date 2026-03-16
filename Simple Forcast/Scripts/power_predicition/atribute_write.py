import requests
import json
import sys
from dotenv import load_dotenv
import os



load_dotenv() 



# =======================
# CONFIGURATION
# =======================

TB_HOST = os.getenv("TB_HOST")   # e.g. http://localhost:8080
USERNAME = os.getenv("TB_USERNAME")
PASSWORD = os.getenv("TB_PASSWORD")
HEADERS = {}

def tb_login():
    url = f"{TB_HOST}/api/auth/login"
    payload = {"username": USERNAME, "password": PASSWORD}
    r = requests.post(url, json=payload)
    r.raise_for_status()
    token = r.json()["token"]
    return {"X-Authorization": f"Bearer {token}"}

def write_device_telemetry(device_id, telemetry):
    url = f"{TB_HOST}/api/plugins/telemetry/ASSET/{device_id}/timeseries/ANY"
    r = requests.post(url, headers=HEADERS, json=telemetry)
    r.raise_for_status()


def atribute_write(asset_id,  daily_power, energy):
    global HEADERS
    try:
        print("[INFO] Logging in to ThingsBoard...")
        HEADERS = tb_login()
        print("[OK] Logged in successfully.")

        for i in range(10):
            print("Sending telemetry data on ",daily_power.index[i].strftime('%Y-%m-%d'))
            telemetry_data = {
                "ts": int(daily_power.index[i].timestamp() * 1000),
                "values": {
                    "daily_energy_kwh_forcast": float(daily_power.iloc[i, 0])
                }
            }
            print(telemetry_data)
            write_device_telemetry(asset_id, telemetry_data)
            print(f"[OK] Sent telemetry: {telemetry_data}")
        print(f"[OK] Sent telemetry: {telemetry_data}")
             
        
        
        
        
    except requests.exceptions.HTTPError as e:
        print("[ERROR] HTTP Error:", e.response.text)
        sys.exit(1)

    except Exception as e:
        print("[ERROR] Error:", str(e))
        sys.exit(1)
