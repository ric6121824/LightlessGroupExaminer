import os
import re

LOG_DIR = r"C:\Users\Ping\AppData\Roaming\XIVLauncher\pluginConfigs\LightlessSync\tracelog"

def detect_active_uid():
    if not os.path.exists(LOG_DIR):
        print("Log dir not found")
        return None
        
    try:
        log_files = sorted([f for f in os.listdir(LOG_DIR) if f.endswith(".log")], key=lambda f: os.path.getmtime(os.path.join(LOG_DIR, f)), reverse=True)
        
        for filename in log_files[:3]:
            file_path = os.path.join(LOG_DIR, filename)
            try:
                file_size = os.path.getsize(file_path)
                read_size = min(100 * 1024, file_size) # last 100KB
                
                with open(file_path, "rb") as f:
                    if file_size > read_size:
                        f.seek(file_size - read_size)
                    chunk = f.read().decode("utf-8", errors="ignore")
                    
                matches = re.findall(r"(?:Using identifier.*UID:\s*([A-Z0-9]+)|GetOAuth2 accessed, returning\s+([A-Z0-9]+))", chunk)
                if matches:
                    print(f"Matches found in {filename}:")
                    for m in matches:
                        print(f"  {m}")
                    for m in reversed(matches):
                        uid = m[0] or m[1]
                        if uid:
                            return uid, filename
            except Exception as e:
                print(f"Error reading log file {filename}: {e}")
    except Exception as e:
        print(f"Error scanning logs: {e}")
        
    return None

result = detect_active_uid()
if result:
    print(f"\nDetected Active UID: {result[0]} from log file: {result[1]}")
else:
    print("\nCould not detect active UID from logs")
