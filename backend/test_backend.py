import subprocess
import time
import urllib.request
import urllib.error
import sys
import os

print("--- Starting FastAPI Server validation ---")

# Run compileall
print("Running python -m compileall app...")
try:
    subprocess.run(["python3", "-m", "compileall", "app"], check=True)
    print("Compileall succeeded!")
except Exception as e:
    print(f"Compileall failed: {e}")

# Start uvicorn with log file output
log_file = open("uvicorn.log", "w")
print("Starting uvicorn app.main:app --host 127.0.0.1 --port 8000 (logging to uvicorn.log)...")
try:
    proc = subprocess.Popen(
        ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=log_file,
        stderr=log_file,
        text=True,
        bufsize=1
    )
except Exception as e:
    print(f"Error starting uvicorn: {e}")
    sys.exit(1)

# Wait 5 seconds for it to start
print("Waiting 5 seconds for server startup...")
time.sleep(5)

# Check if process is still running
status = proc.poll()
if status is not None:
    print(f"Uvicorn failed to start or exited immediately with exit code {status}.")
    log_file.close()
    with open("uvicorn.log", "r") as f:
        print("UVICORN LOGS:")
        print(f.read())
    sys.exit(1)

print("Uvicorn is running. Starting requests verification...")

urls = [
    "http://127.0.0.1:8000/docs",
    "http://127.0.0.1:8000/openapi.json",
    "http://127.0.0.1:8000/api/v1/openapi.json",
    "http://127.0.0.1:8000/api/v1/projects",
    "http://127.0.0.1:8000/api/v1/properties",
    "http://127.0.0.1:8000/api/v1/workflow-executions",
]

for url in urls:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            code = response.getcode()
            print(f"GET {url} -> HTTP {code}")
    except urllib.error.HTTPError as e:
        print(f"GET {url} -> HTTP {e.code} (Error: {e.reason})")
    except urllib.error.URLError as e:
        print(f"GET {url} -> Connection Error: {e.reason}")
    except Exception as e:
        print(f"GET {url} -> Unexpected Error: {e}")

# Kill the process
print("Stopping uvicorn server...")
proc.terminate()
try:
    proc.wait(timeout=3)
except subprocess.TimeoutExpired:
    proc.kill()

log_file.close()

# Print uvicorn logs to see traceback
print("\n--- UVICORN LOGS (LAST 100 LINES) ---")
if os.path.exists("uvicorn.log"):
    with open("uvicorn.log", "r") as f:
        lines = f.readlines()
        for line in lines[-100:]:
            print(line, end="")
else:
    print("Log file not found.")

print("\n--- Validation Finished ---")
