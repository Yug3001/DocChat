import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

root_dir = r"C:\Users\Yug\Desktop\chatbot\frontend"

for root, dirs, files in os.walk(root_dir):
    if "node_modules" in root or ".next" in root:
        continue
    for file in files:
        path = os.path.relpath(os.path.join(root, file), root_dir)
        print(path)
