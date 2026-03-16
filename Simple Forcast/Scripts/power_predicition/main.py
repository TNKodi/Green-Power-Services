from atribute_read import atribute_read
from power import power_prediction
from get_asset import get_all_assets
from atribute_write import atribute_write

asset_ids = "b4ee7360-f4fb-11f0-bef0-af3b94c8901e" #get_all_assets()
print(f"Assets Retrieved: {asset_ids}")

# atributes=atribute_read()
# daily_power, energy = power_prediction(atributes)


atributes = atribute_read(asset_ids)
print(f"Atributes for Asset {asset_ids}: {atributes}")
daily_power, energy = power_prediction(atributes)
atribute_write(asset_ids, daily_power, energy)
