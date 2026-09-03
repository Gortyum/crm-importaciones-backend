"""Levanta el servidor del CRM sin importar desde qué directorio se ejecute.

Uso:
    python run.py
    python run.py --port 9000 --host 0.0.0.0
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn  # noqa: E402


def main():
    host = "0.0.0.0"
    port = int(os.getenv("PORT", "8000"))
    args = sys.argv[1:]
    if "--port" in args:
        port = int(args[args.index("--port") + 1])
    if "--host" in args:
        host = args[args.index("--host") + 1]

    print(f"CRM/ERP backend -> http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
