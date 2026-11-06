from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MachineExperimentConfig:
    mode: str = "MACHINE_VERIFIED_INTERNAL"
    model_id: str = "kimi-k2.5"
    language_model_count: int = 1
    provider_identity_evidence: str = "GATEWAY_MODEL_FIELD_ONLY"
    supplier_invoice: str = "NOT_AVAILABLE"
    provider_fingerprint: str = "UNKNOWN"
    external_publication_certification: bool = False

    def validate(self) -> None:
        if self.model_id != "kimi-k2.5": raise ValueError("V7 permits only kimi-k2.5")
        if self.language_model_count != 1: raise ValueError("V7 requires one base language model")
        if self.mode != "MACHINE_VERIFIED_INTERNAL": raise ValueError("unexpected V7 mode")


def get_config(model_id: str) -> MachineExperimentConfig:
    cfg = MachineExperimentConfig(model_id=model_id); cfg.validate(); return cfg
