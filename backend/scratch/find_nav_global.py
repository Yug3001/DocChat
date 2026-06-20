import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

root_dir = r"C:\Users\Yug\Desktop\chatbot\frontend"

for root, dirs, files in os.walk(root_dir):
    if "node_modules" in root or ".next" in root:
        continue
    for file in files:
        if file.endswith((".tsx", ".ts", ".js", ".jsx")):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                if "Medical" in line or "Database" in line or "Docs" in line:
                    if "nav" in line.lower() or "button" in line.lower() or "style" in line.lower() or "label" in line.lower() or "flex" in line.lower():
                        print(f"{os.path.basename(path)}:{i+1:3d}: {line.strip()[:100]}")
