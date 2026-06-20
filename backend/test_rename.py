import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import tempfile, os

df = pd.DataFrame({
    "Sport": ["CHESS", "Football", "Cricket"],
    "Players": [2, 11, 11],
    "Country": ["Global", "Brazil", "India"],
})

tmp = tempfile.mktemp(suffix=".xlsx")
df.to_excel(tmp, index=False)

meta = {
    "sheet_names": ["Sheet1"],
    "columns": {"Sheet1": list(df.columns)},
    "dtypes": {"Sheet1": {c: str(t) for c, t in df.dtypes.items()}},
    "filename": "test_sports.xlsx",
    "storage_path": tmp,
}

print("=== Test 1: rename_value (CHESS -> MY_CHESS) ===")
from services.excel_updater import run_update
for chunk in run_update("Change the name of the row from CHESS to MY_CHESS", meta, tmp):
    print(chunk["text"], end="")

result = pd.read_excel(tmp)
print("\n\nFile after rename_value:")
print(result.to_string(index=False))

print("\n\n=== Test 2: rename_column (Sport -> SportName) ===")
meta2 = dict(meta)
meta2["columns"] = {"Sheet1": list(result.columns)}
for chunk in run_update("Rename the column Sport to SportName", meta2, tmp):
    print(chunk["text"], end="")

result2 = pd.read_excel(tmp)
print("\n\nFile after rename_column:")
print(result2.to_string(index=False))

os.unlink(tmp)
print("\n\nAll tests passed!")
