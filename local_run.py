import subprocess
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent


def main():
    print("=" * 60)
    print("          FINANCE APP - LOCAL STARTUP")
    print("=" * 60)
    print()
    print("Starting FastAPI backend...")
    print("Starting Streamlit frontend...")
    print()

    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=PROJECT_DIR,
    )

    time.sleep(2)

    frontend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.address",
            "127.0.0.1",
        ],
        cwd=PROJECT_DIR,
    )

    print("Finance App is running.")
    print()
    print("Backend : http://localhost:8000")
    print("API docs: http://localhost:8000/docs")
    print("Frontend: http://localhost:8501")
    print()
    print("Close this window or press Ctrl+C to stop both services.")

    try:
        while True:
            if backend.poll() is not None:
                print("\nFastAPI backend stopped.")
                break

            if frontend.poll() is not None:
                print("\nStreamlit frontend stopped.")
                break

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping Finance App...")

    finally:
        for process in (frontend, backend):
            if process.poll() is None:
                process.terminate()

        for process in (frontend, backend):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        print("Finance App stopped.")


if __name__ == "__main__":
    main()
