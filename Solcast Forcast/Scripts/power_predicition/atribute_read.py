import requests
import sys
import json
import os
import dotenv
dotenv.load_dotenv()

# =======================
# CONFIGURATION
# =======================

TB_HOST = os.getenv("TB_HOST")  # e.g. http://localhost:8080
USERNAME = os.getenv("TB_USERNAME")
PASSWORD = os.getenv("TB_PASSWORD")



ATTRIBUTE_SCOPE = "SERVER_SCOPE"    # SERVER_SCOPE or SHARED_SCOPE

# =======================
# LOGIN
# =======================

def get_jwt_token(tb_host, username, password):
    url = f"{tb_host}/api/auth/login"
    
    response = requests.post(
        url,
        json={
            "username": username,
            "password": password
        }
    )

    response.raise_for_status()
    return response.json()["token"]


# =======================
# READ ATTRIBUTES
# =======================

def read_device_attributes(tb_host, jwt_token, asset_id, scope):
    url = f"{tb_host}/api/plugins/telemetry/ASSET/{asset_id}/values/attributes/{scope}"

    headers = {
        "X-Authorization": f"Bearer {jwt_token}"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


# =======================
# MAIN
# =======================

def atribute_read(asset_id):
    try:
        print("[INFO] Logging in to ThingsBoard...")
        token = get_jwt_token(TB_HOST, USERNAME, PASSWORD)
        print("[OK] Login successful")

        print("[INFO] Reading device attributes...")
        attributes = read_device_attributes(
            TB_HOST,
            token,
            asset_id,
            ATTRIBUTE_SCOPE
        )

        # =======================
        # CONVERT TO KEY-BASED JSON FORMAT
        # =======================
        # Convert list of {key, value} objects to dictionary
        attributes_dict = {item['key']: item['value'] for item in attributes}
        
        print("Attributes as key-based JSON:")
        
        return attributes_dict
        
        # =======================
        # USE VARIABLES
        # =======================
        # Now you can access attributes like:
        # pv_module_model = attributes_dict.get('pv_module_model')
        # system_power_kwp = attributes_dict.get('system_power_kwp')
        
        
        
    except requests.exceptions.HTTPError as e:
        print("❌ HTTP Error:", e.response.text)
        sys.exit(1)

    except Exception as e:
        print("❌ Error:", str(e))
        sys.exit(1)



