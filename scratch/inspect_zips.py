import os
import json
import zipfile

CONFIG_DIR = r"C:\Users\Ping\AppData\Roaming\XIVLauncher\pluginConfigs\LightlessSync"

if os.path.exists(CONFIG_DIR):
    for filename in os.listdir(CONFIG_DIR):
        if filename.startswith("lightless_diagnostics_") and filename.endswith(".zip"):
            zip_path = os.path.join(CONFIG_DIR, filename)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Find JSON report file
                    json_files = [f for f in zip_ref.namelist() if f.startswith("lightless_diagnostics_") and f.endswith(".json")]
                    if json_files:
                        with zip_ref.open(json_files[0]) as f:
                            report = json.load(f)
                            uid = report.get("uid")
                            gen_at = report.get("generatedAt")
                            print(f"Zip: {filename}")
                            print(f"  UID: {uid}")
                            print(f"  Generated At: {gen_at}")
                            
                            # Let's count visible and not-visible pairs
                            txt_files = [f for f in zip_ref.namelist() if f.endswith(".txt") and ("pairs/visible/" in f or "pairs/not-visible/" in f)]
                            print(f"  Pairs: {len(txt_files)}")
            except Exception as e:
                print(f"Error reading {filename}: {e}")
