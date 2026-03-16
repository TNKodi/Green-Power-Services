import requests
import json
import sys

# =======================
# CONFIGURATION
# =======================

TB_HOST = "https://cloud.thingsnode.cc"   # e.g. http://localhost:8080
USERNAME = "nimneththisuka@gmail.com"
PASSWORD = "123@Kodi"

DEVICE_ID = "b4ee7360-f4fb-11f0-bef0-af3b94c8901e"  # UUID

ATTRIBUTE_SCOPE = "SERVER_SCOPE"       # SERVER_SCOPE or SHARED_SCOPE
attributes = {}

# =======================
# LOGIN & GET JWT TOKEN
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
# WRITE ATTRIBUTES
# =======================

def write_device_attributes(tb_host, jwt_token, device_id, attributes, scope):
    url = f"{tb_host}/api/plugins/telemetry/DEVICE/{device_id}/attributes/{scope}"

    headers = {
        "X-Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        headers=headers,
        json=attributes
    )

    response.raise_for_status()
    return response.status_code
def buildinng_type(name):
    if "_S_" in name:
        return "School"
    elif "_H_" in name:
        return "Hospital"
    elif "_L_" in name:
        return "Library"
    
def orientation_setup(data):
    orientations=[]
    no_arrays=data.get("no_arrays")
    for i in range(1,no_arrays+1):
        orientation={
            "tilt":data.get(f"Array {i} Tilt"),
            "azimuth":data.get(f"Array {i} Azimuth"),
            "name":f"0{i}",
            "module_count":data.get(f"Array {i} Number of PV modules")
        }
        orientations.append(orientation)
    return orientations

def atribute_setup(data):
    global attributes
    def to_float(val, default=0.0):
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    attributes={
        "Site_ID": data.get("Project").split('-')[0].strip(),
        "Site_Name": data.get("Project").split('-')[1].strip(),
        "buildingType":buildinng_type(data.get("Project")),
        "isSite": 'true',
        "longitude": data.get("Longitude"),
        "latitude": data.get("Latitude"),
        "altitude": data.get("Altitude"),
        "system_capacity": data.get("System power"),
        "inverter_model": data.get("inverter_model"),
        "inverter_units": data.get("Inverter Units"),
        "inverter_details": f"{data.get('Inverter Units')} x {data.get('inverter_model')}",
        "inverter_power": data.get("Inverter Power"),
        "module_count": data.get("Nb. of modules"),
        "orientation": orientation_setup(data),
        "pv_module_model": data.get("pv_module_model"),
        "pv_module_area":round(float(data.get("Module area"))/int(data.get("Nb. of modules")), 4),
        'iam':{
            "angles": [str(int(a)) if isinstance(a, (int, float)) else str(a) for a in data.get("iam_angles", [])],
            "values": [str(v) for v in data.get("iam_values", [])]
        },
        'losses':{
            "soiling":to_float(data.get("soiling_loss_pct"))/100,
            "lid":to_float(data.get("lid_loss_pct"))/100,
            "module_quality":to_float(data.get("module_quality_loss_pct"))/100,
            "mismatch":to_float(data.get("module_mismatch_loss_pct"))/100,
            "dc_wiring":to_float(data.get("dc_wiring_loss_pct"))/100,
            "ac_wiring":to_float(data.get("ac_wiring_loss_pct"))/100,
            "albedo":to_float(data.get("Albedo")),
            'far_shading':1.0,
           
        }    
    }



# =======================
# MAIN
# =======================

def write_attribute(data):
    global attributes
    try:
        print("🔐 Logging in to ThingsBoard...")
        token = get_jwt_token(TB_HOST, USERNAME, PASSWORD)

        print("✅ Login successful")

        # -------- ATTRIBUTES TO WRITE --------
        atribute_setup(data)
        print(attributes)

        print("📤 Writing attributes to device...")
        status = write_device_attributes(
            TB_HOST,
            token,
            DEVICE_ID,
            attributes,
            ATTRIBUTE_SCOPE
        )

        print(f"✅ Attributes written successfully (HTTP {status})")

    except requests.exceptions.HTTPError as e:
        print("❌ HTTP Error:", e.response.text)
        sys.exit(1)

    except Exception as e:
        print("❌ Error:", str(e))
        sys.exit(1)


