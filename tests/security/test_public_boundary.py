from pathlib import Path
import os
import pytest


FORBIDDEN = ("api_key", "secrets", "credentials", "private_data", "private_oracle", "ground_truth_private")


def test_public_source_tree_has_no_local_secret_directories():
    if "PUBLIC_RELEASE_ROOT" not in os.environ:
        pytest.skip("the working research checkout intentionally contains protected local evidence; CI scans the public release checkout")
    
    root = Path(os.environ["PUBLIC_RELEASE_ROOT"]).resolve()
    for name in FORBIDDEN:
        assert not (root / name).exists(), f"public release must not contain {name}"
