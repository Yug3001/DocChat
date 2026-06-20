import os

sys_dir = r"C:\Users\Yug\Desktop\chatbot\backend\routers"
for root, dirs, files in os.walk(sys_dir):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if "ChatSession" in content:
                print(f"Found in {file}:")
                for i, line in enumerate(content.splitlines()):
                    if "ChatSession" in line:
                        print(f"  {i+1}: {line.strip()}")
