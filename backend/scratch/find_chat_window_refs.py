import os

filepath = r"C:\Users\Yug\Desktop\chatbot\frontend\components\ChatWindow.tsx"
with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "sendMessage" in line or "onNewSession" in line or "useChat" in line or "activeDatasetId" in line:
        if len(line.strip()) < 120:
            print(f"{i+1:3d}: {line.strip()}")
