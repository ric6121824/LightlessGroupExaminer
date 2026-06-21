import os
import re
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
import mimetypes

# Set up paths relative to APPDATA on Windows
APPDATA = os.environ.get('APPDATA')
if APPDATA:
    DEFAULT_CONFIG_DIR = os.path.join(APPDATA, 'XIVLauncher', 'pluginConfigs', 'LightlessSync')
else:
    DEFAULT_CONFIG_DIR = r"C:\Users\Ping\AppData\Roaming\XIVLauncher\pluginConfigs\LightlessSync"

# Cache for zip file UIDs to avoid slow disk I/O when there are many zips
_ZIP_UID_CACHE = {}

class SyncshellAnalyzer:
    def __init__(self, config_dir=DEFAULT_CONFIG_DIR):
        self.config_dir = config_dir
        self.notes_path = os.path.join(config_dir, 'notes.json')
        self.server_path = os.path.join(config_dir, 'server.json')
        self.performance_path = os.path.join(config_dir, 'playerperformance.json')
        self.log_dir = os.path.join(config_dir, 'tracelog')

    def get_available_characters(self):
        # Maps UID -> { "uid": uid, "name": name, "world_id": world_id, "zips": [] }
        characters = {}
        
        # Load from server.json first
        if os.path.exists(self.server_path):
            try:
                with open(self.server_path, "r", encoding="utf-8") as f:
                    server_data = json.load(f)
                    for server in server_data.get("ServerStorage", []):
                        for auth in server.get("Authentications", []):
                            uid = auth.get("UID")
                            name = auth.get("CharacterName")
                            world_id = auth.get("WorldId")
                            if uid and name:
                                characters[uid] = {
                                    "uid": uid,
                                    "name": name,
                                    "world_id": world_id,
                                    "zips": []
                                }
            except Exception as e:
                print(f"Error loading server.json: {e}")

        # Scan all diagnostics zip files in the config folder
        import zipfile
        if os.path.exists(self.config_dir):
            try:
                for filename in os.listdir(self.config_dir):
                    if filename.startswith("lightless_diagnostics_") and filename.endswith(".zip"):
                        zip_path = os.path.join(self.config_dir, filename)
                        mtime = os.path.getmtime(zip_path)
                        
                        # Use cached UID if filename and mtime match
                        uid = None
                        if filename in _ZIP_UID_CACHE:
                            cached_uid, cached_mtime = _ZIP_UID_CACHE[filename]
                            if cached_mtime == mtime:
                                uid = cached_uid
                        
                        if uid is None:
                            try:
                                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                                    # Find JSON report file
                                    json_files = [f for f in zip_ref.namelist() if f.startswith("lightless_diagnostics_") and f.endswith(".json")]
                                    if json_files:
                                        with zip_ref.open(json_files[0]) as f:
                                            report_data = json.load(f)
                                            uid = report_data.get("uid")
                                            if uid:
                                                _ZIP_UID_CACHE[filename] = (uid, mtime)
                            except Exception as e:
                                print(f"Error reading UID from zip {filename}: {e}")
                        
                        if uid and uid != "Not connected":
                            if uid not in characters:
                                characters[uid] = {
                                    "uid": uid,
                                    "name": f"Unknown Character ({uid})",
                                    "world_id": None,
                                    "zips": []
                                }
                            characters[uid]["zips"].append({
                                "filename": filename,
                                "path": zip_path,
                                "mtime": mtime
                            })
            except Exception as e:
                print(f"Error scanning diagnostics zips: {e}")
                
        # Sort zips for each character by filename descending (lexicographical sorting of timestamp guarantees ordering)
        # and fallback to mtime if filenames are identical.
        for uid in characters:
            characters[uid]["zips"].sort(key=lambda x: (x["filename"], x["mtime"]), reverse=True)
            
        return characters

    def detect_active_uid(self):
        if not os.path.exists(self.log_dir):
            return None
            
        try:
            log_files = sorted([f for f in os.listdir(self.log_dir) if f.endswith(".log")], key=lambda f: os.path.getmtime(os.path.join(self.log_dir, f)), reverse=True)
            
            for filename in log_files[:3]:
                file_path = os.path.join(self.log_dir, filename)
                try:
                    file_size = os.path.getsize(file_path)
                    read_size = min(100 * 1024, file_size) # last 100KB
                    
                    with open(file_path, "rb") as f:
                        if file_size > read_size:
                            f.seek(file_size - read_size)
                        chunk = f.read().decode("utf-8", errors="ignore")
                        
                    matches = re.findall(r"(?:Using identifier.*UID:\s*([A-Z0-9]+)|GetOAuth2 accessed, returning\s+([A-Z0-9]+))", chunk)
                    if matches:
                        for m in reversed(matches):
                            uid = m[0] or m[1]
                            if uid:
                                return uid
                except Exception as e:
                    print(f"Error scanning log end for active UID {filename}: {e}")
        except Exception as e:
            print(f"Error scanning logs for active UID: {e}")
            
        return None

    def parse_zip_timestamp(self, filename):
        match = re.search(r"lightless_diagnostics_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})\.zip", filename)
        if match:
            date_str = match.group(1)
            time_str = f"{match.group(2)}:{match.group(3)}:{match.group(4)}"
            return f"{date_str} {time_str}"
        return "Unknown Date/Time"

    def analyze(self, selected_uid=None):
        # 1. Load user/group comment mappings from notes.json
        notes_gid_names = {}
        notes_uid_names = {}
        if os.path.exists(self.notes_path):
            try:
                with open(self.notes_path, "r", encoding="utf-8") as f:
                    notes_data = json.load(f)
                    server_notes = notes_data.get("ServerNotes", {})
                    for server_uri, notes in server_notes.items():
                        notes_gid_names.update(notes.get("GidServerComments", {}))
                        notes_uid_names.update(notes.get("UidServerComments", {}))
            except Exception as e:
                print(f"Error loading notes.json: {e}")

        # 2. Gather additional UID -> Name mappings from other config files
        config_uid_names = {}
        
        # From server.json (own characters)
        if os.path.exists(self.server_path):
            try:
                with open(self.server_path, "r", encoding="utf-8") as f:
                    server_data = json.load(f)
                    for server in server_data.get("ServerStorage", []):
                        for auth in server.get("Authentications", []):
                            uid = auth.get("UID")
                            name = auth.get("CharacterName")
                            if uid and name:
                                config_uid_names[uid] = f"{name} (Self)"
            except Exception as e:
                print(f"Error loading server.json: {e}")

        # From playerperformance.json (paused users)
        if os.path.exists(self.performance_path):
            try:
                with open(self.performance_path, "r", encoding="utf-8") as f:
                    perf_data = json.load(f)
                    for history in perf_data.get("AutoPauseHistory", []):
                        uid = history.get("UID")
                        name = history.get("PlayerName")
                        if uid and name:
                            config_uid_names[uid] = name
            except Exception as e:
                print(f"Error loading playerperformance.json: {e}")

        # Build characters list & identify active UID
        characters = self.get_available_characters()
        active_uid = self.detect_active_uid()
        
        # Determine current character UID to show
        current_uid = None
        if selected_uid and selected_uid in characters:
            current_uid = selected_uid
        elif active_uid and active_uid in characters:
            current_uid = active_uid
        else:
            # Pick character with most recent zip report
            latest_zip_time = -1
            for uid, char_data in characters.items():
                if char_data["zips"]:
                    zip_time = char_data["zips"][0]["mtime"]
                    if zip_time > latest_zip_time:
                        latest_zip_time = zip_time
                        current_uid = uid
            # Fallback
            if not current_uid:
                current_uid = active_uid or (list(characters.keys())[0] if characters else None)

        # 3. Parse diagnostics report zip if found, otherwise fall back to logs chronologically
        groups = {}
        log_uid_names = {}
        
        data_source = "logs_incomplete"
        diagnostics_timestamp = None
        diagnostics_file = None

        # Try to load zip for the current character
        zip_path = None
        zip_name = None
        if current_uid and current_uid in characters and characters[current_uid]["zips"]:
            zip_name = characters[current_uid]["zips"][0]["filename"]
            zip_path = characters[current_uid]["zips"][0]["path"]

        if zip_path:
            import zipfile
            try:
                print(f"Parsing diagnostics report for {current_uid}: {zip_path}")
                diagnostics_file = zip_name
                diagnostics_timestamp = self.parse_zip_timestamp(zip_name)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Scan for files matching pairs/visible/{uid}.txt or pairs/not-visible/{uid}.txt
                    for file_info in zip_ref.infolist():
                        filepath = file_info.filename
                        if filepath.endswith(".txt") and (filepath.startswith("pairs/visible/") or filepath.startswith("pairs/not-visible/")):
                            # Extract uid
                            uid = os.path.basename(filepath)[:-4]
                            
                            try:
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
                                    
                                    # Parse Player Name
                                    if line_strip.startswith("Player Name:"):
                                        p_name = line_strip[len("Player Name:"):].strip()
                                        if p_name and p_name != "(not cached)":
                                            player_name = p_name
                                        continue
                                    
                                    # Parse Alias
                                    if line_strip.startswith("Alias:"):
                                        p_alias = line_strip[len("Alias:"):].strip()
                                        if p_alias and p_alias != "(none)":
                                            player_alias = p_alias
                                        continue
                                    
                                    # Parse Note
                                    if line_strip.startswith("Note:"):
                                        p_note = line_strip[len("Note:"):].strip()
                                        if p_note and p_note != "(none)":
                                            player_note = p_note
                                        continue
                                        
                                    if line_strip == "Syncshell Memberships":
                                        in_memberships = True
                                        continue
                                        
                                    if in_memberships:
                                        if line_strip == "Not a member of any syncshells.":
                                            continue
                                        
                                        # Format: <AliasOrGID> [<GID>]{flags}
                                        match = re.match(r"^(.*?)\s+\[([^\]]+)\](?:\s+\((.*?)\))?$", line_strip)
                                        if match:
                                            alias_or_gid = match.group(1).strip()
                                            gid = match.group(2).strip()
                                            
                                            group_alias = alias_or_gid if alias_or_gid != gid else ""
                                            
                                            if gid not in groups:
                                                groups[gid] = {
                                                    "gid": gid,
                                                    "alias": group_alias,
                                                    "notes_name": notes_gid_names.get(gid, ""),
                                                    "members": set()
                                                }
                                            if group_alias and not groups[gid]["alias"]:
                                                groups[gid]["alias"] = group_alias
                                                
                                            groups[gid]["members"].add(uid)
                                
                                # Store player names, preferring note -> name -> alias
                                name_resolved = player_note or player_name or player_alias
                                if name_resolved:
                                    log_uid_names[uid] = name_resolved
                                    
                            except Exception as e:
                                print(f"Error parsing diagnostic entry {filepath}: {e}")
                
                data_source = "diagnostics_report"
            except Exception as e:
                print(f"Error reading zip file {zip_path}: {e}. Falling back to trace logs.")

        # Fallback to trace logs if no diagnostics zip is found
        if data_source == "logs_incomplete":
            joined_pattern = re.compile(
                r"Client_GroupPairJoined:\s+GroupPairFullInfoDto\s+\{\s+Group\s+=\s+GroupData\s+\{\s+GID\s+=\s+(?P<gid>[^,\s}]+)(?:,\s+Alias\s+=\s+(?P<alias>[^,\s}]*))?.*?\},\s+GID\s+=\s+[^,]+,\s+GroupAlias\s+=\s+(?P<galias>[^,]*?),\s+GroupAliasOrGID\s+=\s+[^,]+,\s+User\s+=\s+UserData\s+\{\s+UID\s+=\s+(?P<uid>[^,\s}]+)(?:,\s+Alias\s+=\s+(?P<user_alias>[^,\s}]*))?.*?\},\s+UID\s+=\s+[^,]+,\s+UserAlias\s+=\s+(?P<ualias>[^,]*?),\s+UserAliasOrUID\s+=\s+[^,]+"
            )

            left_pattern = re.compile(
                r"Client_GroupPairLeft:\s+GroupPairDto\s+\{\s+Group\s+=\s+GroupData\s+\{\s+GID\s+=\s+(?P<gid>[^,\s}]+).*?\},\s+GID\s+=\s+[^,]+,\s+GroupAlias\s+=\s+(?P<galias>[^,]*?),\s+GroupAliasOrGID\s+=\s+[^,]+,\s+User\s+=\s+UserData\s+\{\s+UID\s+=\s+(?P<uid>[^,\s}]+).*?\},\s+UID\s+=\s+[^,]+,\s+UserAlias\s+=\s+(?P<ualias>[^,]*?),\s+UserAliasOrUID\s+=\s+[^,]+"
            )

            if os.path.exists(self.log_dir):
                log_files = sorted([f for f in os.listdir(self.log_dir) if f.endswith(".log")])
                for filename in log_files:
                    file_path = os.path.join(self.log_dir, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                if "Client_GroupPairJoined" in line:
                                    match = joined_pattern.search(line)
                                    if match:
                                        gid = match.group("gid")
                                        uid = match.group("uid")
                                        galias = match.group("alias") or match.group("galias") or ""
                                        ualias = match.group("user_alias") or match.group("ualias") or ""
                                        
                                        galias = galias.strip()
                                        ualias = ualias.strip()
                                        
                                        if gid not in groups:
                                            groups[gid] = {
                                                "gid": gid,
                                                "alias": galias,
                                                "notes_name": notes_gid_names.get(gid, ""),
                                                "members": set()
                                            }
                                        if galias and not groups[gid]["alias"]:
                                            groups[gid]["alias"] = galias
                                            
                                        groups[gid]["members"].add(uid)
                                        if ualias:
                                            log_uid_names[uid] = ualias
                                elif "Client_GroupPairLeft" in line:
                                    match = left_pattern.search(line)
                                    if match:
                                        gid = match.group("gid")
                                        uid = match.group("uid")
                                        if gid in groups and uid in groups[gid]["members"]:
                                            groups[gid]["members"].remove(uid)
                    except Exception as e:
                        print(f"Error parsing log file {filename}: {e}")


        # Combine all name sources for UIDs
        # Priority: notes.json comment > server.json/playerperformance.json > trace logs/zip files > default (UID)
        final_members = {}
        all_uids = set()
        for gid, gdata in groups.items():
            all_uids.update(gdata["members"])
            
        for uid in all_uids:
            name = notes_uid_names.get(uid, "") or config_uid_names.get(uid, "") or log_uid_names.get(uid, "") or uid
            final_members[uid] = name

        # 4. Perform overlap and redundancy analysis
        group_list = []
        for gid, gdata in groups.items():
            members_set = gdata["members"]
            
            # Find all members in OTHER groups
            other_members = set()
            for other_gid, other_gdata in groups.items():
                if other_gid != gid:
                    other_members.update(other_gdata["members"])
                    
            shared_members = members_set.intersection(other_members)
            unique_members = members_set.difference(other_members)
            
            # Find detailed overlaps with each individual group
            overlaps = {}
            for other_gid, other_gdata in groups.items():
                if other_gid != gid:
                    shared_with_other = members_set.intersection(other_gdata["members"])
                    if shared_with_other:
                        overlaps[other_gid] = len(shared_with_other)

            total_count = len(members_set)
            shared_count = len(shared_members)
            unique_count = len(unique_members)
            
            redundancy_pct = (shared_count / total_count * 100) if total_count > 0 else 0
            
            # Determine Leave Impact
            # 0: None, 1-3: Low, 4-10: Medium, >10: High
            if unique_count == 0:
                leave_impact = "None"
            elif unique_count <= 3:
                leave_impact = "Low"
            elif unique_count <= 10:
                leave_impact = "Medium"
            else:
                leave_impact = "High"

            group_list.append({
                "gid": gid,
                "alias": gdata["alias"],
                "notes_name": gdata["notes_name"],
                "name": gdata["notes_name"] or gdata["alias"] or gid,
                "total_members": total_count,
                "shared_members_count": shared_count,
                "unique_members_count": unique_count,
                "redundancy_pct": round(redundancy_pct, 1),
                "leave_impact": leave_impact,
                "shared_members": list(shared_members),
                "unique_members": list(unique_members),
                "overlaps": overlaps
            })

        # Sort groups by unique members count (ascending) to show lowest impact first
        group_list.sort(key=lambda g: g["unique_members_count"])

        # Summary statistics
        total_unique_players = len(all_uids)
        avg_redundancy = sum(g["redundancy_pct"] for g in group_list) / len(group_list) if group_list else 0
        
        # Recommendations: Groups with 0 unique members are perfectly redundant (can leave without losing anyone)
        safe_to_leave = [g["gid"] for g in group_list if g["unique_members_count"] == 0]

        summary = {
            "total_groups": len(group_list),
            "total_unique_players": total_unique_players,
            "average_redundancy_pct": round(avg_redundancy, 1),
            "safe_to_leave_gids": safe_to_leave
        }

        # Build characters list for response
        characters_list = []
        for uid, char_data in characters.items():
            characters_list.append({
                "uid": uid,
                "name": char_data["name"],
                "has_report": len(char_data["zips"]) > 0,
                "is_active": uid == active_uid,
                "is_current": uid == current_uid
            })

        return {
            "groups": group_list,
            "members": final_members,
            "summary": summary,
            "data_source": data_source,
            "diagnostics_timestamp": diagnostics_timestamp,
            "diagnostics_file": diagnostics_file,
            "characters": characters_list,
            "current_character": current_uid
        }

# Web server handling requests
class HTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress logging every request to stdout to keep it clean
        pass

    def do_GET(self):
        if self.path.startswith('/api/data'):
            try:
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)
                selected_uid = query_params.get('uid', [None])[0]

                analyzer = SyncshellAnalyzer()
                data = analyzer.analyze(selected_uid)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        # Serve static files from 'public' directory
        public_dir = os.path.join(os.path.dirname(__file__), 'public')
        
        # Normalize request path
        req_path = self.path.split('?')[0] # remove query parameters
        if req_path == '/' or req_path == '':
            file_path = os.path.join(public_dir, 'index.html')
        else:
            file_path = os.path.join(public_dir, req_path.lstrip('/'))

        # Check if file exists and is within the public folder
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = 'application/octet-stream'
                
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.end_headers()
                
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Internal server error: {e}".encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

def run(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, HTTPHandler)
    print(f"Starting server on http://localhost:{port}...")
    webbrowser.open(f"http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        httpd.server_close()

if __name__ == '__main__':
    run()
