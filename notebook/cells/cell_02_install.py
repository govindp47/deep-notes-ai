# ─── Cell 2: Install Dependencies ────────────────────────────────────────────
import sys

print("Installing dependencies…")
packages = [
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "langchain-core>=0.3.0",
    "qdrant-client>=1.7.0",
    "neo4j>=5.0.0",
    "tiktoken>=0.7.0",
    "tenacity>=8.0.0",
    "youtube-transcript-api>=0.6.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
    "requests>=2.31.0",
]

import subprocess
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "--upgrade"] + packages,
    capture_output=True, text=True
)
if result.returncode != 0:
    print("STDERR:", result.stderr[-2000:])
else:
    print("✅ All dependencies installed successfully")
