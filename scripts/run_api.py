#!/usr/bin/env python
"""Run the API server."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("Preventive Health Assistant API")
    print("=" * 60)
    print("\n🚀 Starting server at http://127.0.0.1:8000")
    print("📚 API Docs: http://127.0.0.1:8000/docs")
    print("\nPress Ctrl+C to stop\n")

    uvicorn.run(
        "src.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )