from pathlib import Path

from scientific_discovery.project.cli import run_experiments
from scientific_discovery.project.offline import validate_result
from scientific_discovery.project.registry import EXPERIMENT_IDS, load_registry


def test_all_experiments_have_offline_smoke_contract(tmp_path: Path):
    registry = load_registry()
    run_experiments(EXPERIMENT_IDS, tmp_path)
    for experiment_id in EXPERIMENT_IDS:
        result = tmp_path / experiment_id.replace(".", "_") / "result.json"
        assert validate_result(result) == []
        assert result.exists()
        assert registry[experiment_id].experiment_id == experiment_id
