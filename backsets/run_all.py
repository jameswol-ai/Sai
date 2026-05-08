# backtests/run_all.py
import glob
import subprocess
import sys

def run_backtests():
    backtest_files = glob.glob("backtests/strategies/*.py")
    results = {}

    for file in backtest_files:
        print(f"Running backtest: {file}")
        try:
            result = subprocess.run([sys.executable, file], capture_output=True, text=True)
            results[file] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            results[file] = {"error": str(e)}

    return results

if __name__ == "__main__":
    results = run_backtests()
    for file, outcome in results.items():
        if "error" in outcome:
            print(f"❌ {file} failed with error: {outcome['error']}")
        elif outcome["returncode"] != 0:
            print(f"❌ {file} failed:\n{outcome['stderr']}")
        else:
            print(f"✅ {file} passed:\n{outcome['stdout']}")
