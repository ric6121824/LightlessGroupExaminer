import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import SyncshellAnalyzer

try:
    analyzer = SyncshellAnalyzer()
    print("Configuration Directory:", analyzer.config_dir)
    data = analyzer.analyze()
    print("API Data Keys:", list(data.keys()))
    print("Data Source:", data.get("data_source"))
    print("Diagnostics File:", data.get("diagnostics_file"))
    print("Diagnostics Timestamp:", data.get("diagnostics_timestamp"))
    print("Summary:", data.get("summary"))
    print("Number of parsed groups:", len(data.get("groups", [])))
    print("Number of parsed members:", len(data.get("members", {})))
except Exception as e:
    import traceback
    traceback.print_exc()
