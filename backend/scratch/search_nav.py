import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

filepath = r"C:\Users\Yug\Desktop\chatbot\frontend\components\ChatWindow.tsx"
if not os.path.exists(filepath):
    print("File not found:", filepath)
    exit()

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    line_lower = line.lower()
    if "medical" in line_lower or "database" in line_lower or "scraped" in line_lower:
        print(f"{i+1:3d}: {line.strip()[:120]}")
