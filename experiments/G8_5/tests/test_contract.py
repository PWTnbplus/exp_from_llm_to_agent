from pathlib import Path
import json
def test_contract_files_exist():
    root = Path(__file__).parents[1]
    assert (root / "README.md").exists()
    assert json.loads((root / "config.yaml").read_text())["experiment_id"] == "G8.5"
