import os

filepath = r"C:\Users\Yug\Desktop\chatbot\backend\routers\dataset.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

for i, line in enumerate(content.splitlines()):
    if "message" in line.lower() or "db.add" in line.lower() or "session" in line.lower() or "chat" in line.lower():
        if len(line.strip()) < 120:
            print(f"{i+1:3d}: {line.strip()}")
