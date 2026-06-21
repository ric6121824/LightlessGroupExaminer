import os
import re
import json
import zipfile

def create_mock_zip(zip_path):
    pairs_data = {
        "visible/uid_player1.txt": """Lightless Pair Diagnostics
Generated: 6/20/2026 2:00:00 PM

Pair
Alias/UID: PlayerOneAlias
UID: uid_player1
Alias: PlayerOneAlias
Player Name: Player One
Handler Ident: something
Individual Status: Paired
Any Connection: True
Paused: False
Visible: True
Online: True
Note: Player One Note

Syncshell Memberships
LLS-GR1NN2055TUF (Creampuff SPA) [LLS-GR1NN2055TUF]
LLS-GR2NN2055TUF [LLS-GR2NN2055TUF]

Pair DTO Snapshot
{"uid": "uid_player1"}
""",
        "not-visible/uid_player2.txt": """Lightless Pair Diagnostics
Generated: 6/20/2026 2:01:00 PM

Pair
Alias/UID: uid_player2
UID: uid_player2
Alias: (none)
Player Name: Player Two
Paused: False
Visible: False
Online: False
Note: (none)

Syncshell Memberships
LLS-GR1NN2055TUF (Creampuff SPA) [LLS-GR1NN2055TUF] (Moderator)
LLS-GR3NN2055TUF [LLS-GR3NN2055TUF]
"""
    }
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for filepath, content in pairs_data.items():
            zf.writestr(f"pairs/{filepath}", content)

def test_parse(zip_path):
    groups = {}
    uid_names = {}
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_info in zip_ref.infolist():
            filepath = file_info.filename
            if filepath.endswith(".txt") and (filepath.startswith("pairs/visible/") or filepath.startswith("pairs/not-visible/")):
                uid = os.path.basename(filepath)[:-4]
                print(f"Found pair file: {filepath} for UID: {uid}")
                
                with zip_ref.open(file_info) as f:
                    content = f.read().decode('utf-8', errors='ignore')
                
                player_name = None
                player_note = None
                player_alias = None
                in_memberships = False
                
                for line in content.splitlines():
                    line_strip = line.strip()
                    if not line_strip:
                        if in_memberships:
                            in_memberships = False
                        continue
                    
                    if line_strip.startswith("Player Name:"):
                        p_name = line_strip[len("Player Name:"):].strip()
                        if p_name and p_name != "(not cached)":
                            player_name = p_name
                    elif line_strip.startswith("Alias:"):
                        p_alias = line_strip[len("Alias:"):].strip()
                        if p_alias and p_alias != "(none)":
                            player_alias = p_alias
                    elif line_strip.startswith("Note:"):
                        p_note = line_strip[len("Note:"):].strip()
                        if p_note and p_note != "(none)":
                            player_note = p_note
                    elif line_strip == "Syncshell Memberships":
                        in_memberships = True
                    elif in_memberships:
                        if line_strip == "Not a member of any syncshells.":
                            continue
                        
                        match = re.match(r"^(.*?)\s+\[([^\]]+)\](?:\s+\((.*?)\))?$", line_strip)
                        if match:
                            alias_or_gid = match.group(1).strip()
                            gid = match.group(2).strip()
                            flags = match.group(3).strip() if match.group(3) else ""
                            
                            group_alias = alias_or_gid if alias_or_gid != gid else ""
                            
                            print(f"  Parsed membership: GID='{gid}', Alias='{group_alias}', Flags='{flags}'")
                            
                            if gid not in groups:
                                groups[gid] = {
                                    "gid": gid,
                                    "alias": group_alias,
                                    "members": set()
                                }
                            if group_alias and not groups[gid]["alias"]:
                                groups[gid]["alias"] = group_alias
                            groups[gid]["members"].add(uid)
                
                # Resolve player name
                resolved_name = player_note or player_name or player_alias
                if resolved_name:
                    uid_names[uid] = resolved_name
                    print(f"  Resolved Player Name: '{resolved_name}'")

    print("\n--- Summary of parsed groups ---")
    for gid, data in groups.items():
        print(f"Group: {data['alias'] or gid} ({gid})")
        print(f"  Members: {list(data['members'])}")
        
    print("\n--- Summary of resolved names ---")
    for uid, name in uid_names.items():
        print(f"  {uid}: {name}")

if __name__ == "__main__":
    zip_path = "mock_diagnostics.zip"
    create_mock_zip(zip_path)
    try:
        test_parse(zip_path)
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
