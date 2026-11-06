from scientific_discovery.project.registry import EXPERIMENT_IDS, load_registry, topological_order


def test_registry_contains_all_experiments_in_canonical_order():
    registry = load_registry()
    assert tuple(registry) == EXPERIMENT_IDS
    assert set(topological_order(registry)) == set(EXPERIMENT_IDS)
    assert registry["G8.5"].dependencies == ("G8",)


def test_registry_keeps_status_dimensions_separate():
    registry = load_registry()
    assert registry["G0"].implementation_status == "IMPLEMENTED"
    assert registry["G9"].implementation_status == "PARTIAL"
    assert registry["G9"].reproducibility_status == "BLOCKED"
