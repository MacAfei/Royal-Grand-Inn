import subprocess
import time
import os
import sys

print("Python executable:", sys.executable)
print("Cwd:", os.getcwd())

# Launch app.py using venv python
python_bin = os.path.join("venv", "Scripts", "python.exe")
if not os.path.exists(python_bin):
    python_bin = "python"

print("Using python bin:", python_bin)

# Run process
proc = subprocess.Popen(
    [python_bin, "app.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Wait 5 seconds to capture output
time.sleep(5)

# Terminate it so it closes pipes
proc.terminate()

# Now read whatever was printed
stdout, stderr = proc.communicate()
print("--- STDOUT ---")
print(stdout)
print("--- STDERR ---")
print(stderr)
