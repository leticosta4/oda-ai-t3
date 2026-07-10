import os
import json
from db.client import db
from etl.common import PROCESSED_DATA_DIR
from etl.dgp import save_group_to_db
from etl.lattes import save_lattes_to_db

async def run_all():
    print("=== RUNNING ETL FOR ALL GROUPS AND RESEARCHERS ===")
    
    dgp_dir = os.path.join(PROCESSED_DATA_DIR, 'dgp')
    lattes_dir = os.path.join(PROCESSED_DATA_DIR, 'lattes')
    
    if not os.path.exists(dgp_dir):
        print(f"DGP directory not found: {dgp_dir}")
        return
        
    group_files = [f for f in os.listdir(dgp_dir) if f.endswith('.json')]
    print(f"Found {len(group_files)} groups in processed-data.")
    
    for group_file in group_files:
        group_file_path = os.path.join(dgp_dir, group_file)
        print(f"\n--------------------------------------------")
        print(f"[ETL-ALL] Processing Group: {group_file}")
        
        with open(group_file_path, "r", encoding="utf-8") as f:
            group_data = json.load(f)
            
        # 1. Process group
        await save_group_to_db(group_data)
        
        # 2. Process members
        membros = group_data.get("membros", [])
        if isinstance(membros, list):
            print(f"[ETL-ALL] Group has {len(membros)} members. Checking files...")
            for membro in membros:
                lattes_id = membro.get("lattes")
                if not lattes_id:
                    continue
                lattes_file_name = f"{lattes_id.strip()}.json"
                lattes_file_path = os.path.join(lattes_dir, lattes_file_name)
                
                if os.path.exists(lattes_file_path):
                    print(f"[ETL-ALL] Processing Researcher Lattes: {membro.get('nome')} ({lattes_id})")
                    with open(lattes_file_path, "r", encoding="utf-8") as f_lat:
                        lattes_data = json.load(f_lat)
                    await save_lattes_to_db(lattes_data)
                else:
                    print(f"[ETL-ALL] Lattes file NOT found for: {membro.get('nome')} ({lattes_id})")
                    
    print("\n=== ETL RUN ALL COMPLETED ===")
