import requests
import os
import dotenv

dotenv.load_dotenv()


TB_HOST = os.getenv("TB_HOST")
USERNAME = os.getenv("TB_USERNAME")
PASSWORD = os.getenv("TB_PASSWORD")

ROOT_ASSET_ID = os.getenv("ASSET_ID")
TARGET_LEVEL = int(os.getenv("TARGET_LEVEL"))

def tb_login():
    url = f"{TB_HOST}/api/auth/login"
    payload = {"username": USERNAME, "password": PASSWORD}
    r = requests.post(url, json=payload)
    r.raise_for_status()
    token = r.json()["token"]
    return {"X-Authorization": f"Bearer {token}"}
HEADERS = tb_login()
print("[OK] Logged into ThingsBoard")

def get_asset_children(asset_id):
    url=f"{TB_HOST}/api/relations/info"
    params={"fromId": asset_id, "fromType": "ASSET"}
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()

    children = []
    for rel in r.json():
        if rel["to"]["entityType"] == "ASSET" and rel["type"] == "Contains":
            children.append(rel["to"]["id"])
    return children

def get_assets_by_level():
    current_assets=[ROOT_ASSET_ID]
    ext_assets = []
    for _ in range(1, TARGET_LEVEL+1):
        next_assets = []
        for aid in current_assets:
            next_assets.extend(get_asset_children(aid))
        current_assets = next_assets
        print(f"[OK] Retrieved assets at level {_}: {len(current_assets)} assets found")
        if not current_assets:
            print("[WARNING] No more assets found at this level. Exiting.")
            break
    return current_assets

    




def get_all_assets():
    tb_login()
    level_3_assets = get_assets_by_level()
    return level_3_assets


if __name__=="__main__":
    get_all_assets()
    


