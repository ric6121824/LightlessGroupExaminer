import os
import sys
import zipfile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import SyncshellAnalyzer

CONFIG_DIR = r"C:\Users\Ping\AppData\Roaming\XIVLauncher\pluginConfigs\LightlessSync"
mock_zip_name = "lightless_diagnostics_2026-06-20_14-00-00.zip"
mock_zip_path = os.path.join(CONFIG_DIR, mock_zip_name)

pairs_data = {
    "visible/uid_test_alpha.txt": """Lightless Pair Diagnostics
Generated: 6/20/2026 2:00:00 PM

Pair
Alias/UID: AlphaAlias
UID: uid_test_alpha
Player Name: Alpha Player
Note: Note for Alpha

Syncshell Memberships
Creampuff SPA [LLS-GR1NN2055TUF]
Some Other Group [LLS-GR2NN2055TUF]
""",
    "not-visible/uid_test_beta.txt": """Lightless Pair Diagnostics
Generated: 6/20/2026 2:01:00 PM

Pair
UID: uid_test_beta
Player Name: Beta Player

Syncshell Memberships
Creampuff SPA [LLS-GR1NN2055TUF]
"""
}

print(f"Creating mock zip at: {mock_zip_path}")
try:
    with zipfile.ZipFile(mock_zip_path, 'w') as zf:
        for filepath, content in pairs_data.items():
            zf.writestr(f"pairs/{filepath}", content)
            
    analyzer = SyncshellAnalyzer()
    data = analyzer.analyze()
    
    print("\n--- Parsing Results with Mock Zip ---")
    print("Data Source:", data.get("data_source"))
    print("Diagnostics File:", data.get("diagnostics_file"))
    print("Diagnostics Timestamp:", data.get("diagnostics_timestamp"))
    print("Total parsed groups:", len(data.get("groups", [])))
    print("Total parsed members:", len(data.get("members", {})))
    
    # Check if we parsed our mock members
    members = data.get("members", {})
    print("uid_test_alpha name:", members.get("uid_test_alpha"))
    print("uid_test_beta name:", members.get("uid_test_beta"))
    
    # Check Creampuff SPA group details
    groups = data.get("groups", [])
    creampuff_spa = [g for g in groups if g["gid"] == "LLS-GR1NN2055TUF"]
    if creampuff_spa:
        g = creampuff_spa[0]
        print("\nFound Creampuff SPA:")
        print(f"  Name: {g['name']}")
        print(f"  Total Members: {g['total_members']}")
        print(f"  Shared: {g['shared_members_count']}")
        print(f"  Unique: {g['unique_members_count']}")
        print(f"  Leave Impact: {g['leave_impact']}")
        print(f"  Overlaps:", g['overlaps'])
    else:
        print("\nCreampuff SPA group not found!")

finally:
    print(f"\nCleaning up mock zip at: {mock_zip_path}")
    if os.path.exists(mock_zip_path):
        os.remove(mock_zip_path)
