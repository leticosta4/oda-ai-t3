import os
import json

ROOT_DIR = os.getcwd()
DATA_DIR = os.path.abspath(os.path.join(ROOT_DIR, "data"))
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw-data")
DGP_DATA_DIR = os.path.join(RAW_DATA_DIR, "dgp")
LATTES_DATA_DIR = os.path.join(RAW_DATA_DIR, "lattes")
IMAGE_DIR = os.path.abspath(os.path.join(ROOT_DIR, "static"))

for d in [DATA_DIR, RAW_DATA_DIR, DGP_DATA_DIR, LATTES_DATA_DIR, IMAGE_DIR]:
    os.makedirs(d, exist_ok=True)

def save_json(data, directory, file_name):
    file_path = os.path.join(directory, f"{file_name}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
