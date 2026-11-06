from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experiments._shared import evaluate_cli
if __name__ == "__main__": raise SystemExit(evaluate_cli("G2"))
