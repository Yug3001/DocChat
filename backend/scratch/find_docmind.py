import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

root_dir = r"C:\Users\Yug\Desktop\chatbot"

for root, dirs, files in os.walk(root_dir):
    if "node_modules" in root or ".next" in root or ".git" in root:
        continue
    for file in files:
        if file.endswith((".tsx", ".ts", ".js", ".jsx", ".css", ".py", ".md", ".html")):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "DocMind" in content or "RAG Assistant" in content or "Medical" in content or "Database" in content:
                    # print where it is found
                    lines = content.splitlines()
                    for idx, line in enumerate(lines):
                        if "DocMind" in line or "RAG Assistant" in line:
                            print(f"{os.path.relpath(path, root_dir)}:{idx+1}: {line.strip()}")
            except Exception as e:
                pass
