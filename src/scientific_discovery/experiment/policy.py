"""Hard execution policies for the five controlled experiment groups.

The policies are deliberately enforced around the provider and tool boundary.
Prompt text is descriptive only; it is never the mechanism that grants or
removes an experiment capability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


class PolicyViolation(RuntimeError):
    """Raised when a runner attempts an action outside its registered group."""


@dataclass(frozen=True)
class GroupPolicy:
    group: str
    name: str
    max_model_calls: int
    max_tool_calls: int
    max_compute_steps: int
    max_experiments: int
    max_api_calls: int
    max_transport_retries: int
    allowed_tools: tuple[str, ...]
    planning: str
    allow_memory: bool
    allow_retrieval: bool
    memory_items: int = 0
    max_input_tokens: int = 100_000
    max_output_tokens: int = 30_000

    def as_dict(self) -> dict[str, Any]:
        return asdict(self) | {"allowed_tools": list(self.allowed_tools)}


# G1 isolates model capability. G2 adds bounded deterministic calculation,
# G3 adds a fixed second-pass reflection, G4 adds adaptive tool use, and G5
# adds only run-local bounded memory to the adaptive workflow. No group has
# external retrieval; that would introduce an uncontrolled training-data and
# corpus confound.
GROUP_POLICIES: dict[str, GroupPolicy] = {
    "G1": GroupPolicy(
        "G1", "llm_only", 2, 0, 0, 6, 2, 0, (), "one_shot", False, False,
    ),
    "G2": GroupPolicy(
        "G2", "llm_with_fixed_tools", 2, 4, 4, 0, 2, 0,
        ("calculate_expression",), "fixed_tool_assist", False, False,
    ),
    "G3": GroupPolicy(
        "G3", "llm_with_reflection", 2, 0, 0, 6, 2, 0, (), "fixed_reflection", False, False,
    ),
    "G4": GroupPolicy(
        "G4", "single_agent", 8, 6, 0, 6, 8, 0,
        ("run_experiment", "calculate_expression"), "adaptive", False, False,
    ),
    "G5": GroupPolicy(
        "G5", "single_agent_with_bounded_memory", 10, 10, 4, 6, 10, 0,
        ("run_experiment", "calculate_expression"), "adaptive_memory", True, False, 32,
    ),
}

GROUP_ALIASES = {
    "g1": "G1", "g2": "G2", "g3": "G3", "g4": "G4", "g5": "G5",
    "llm_only": "G1", "llm_tools": "G2", "iterative_reflection": "G3",
    "agent": "G4", "single_agent": "G4",
}


def get_group_policy(group: str) -> GroupPolicy:
    key = GROUP_ALIASES.get(str(group).lower(), str(group).upper())
    try:
        return GROUP_POLICIES[key]
    except KeyError as exc:
        raise ValueError(f"unknown experiment group: {group}") from exc


class PolicyController:
    """Counters and permission checks shared by provider and tool execution."""

    def __init__(self, policy: GroupPolicy, *, trace: Any = None):
        self.policy = policy
        self.trace = trace
        self.model_calls = 0
        self.tool_calls = 0
        self.compute_steps = 0
        self.memory_items = 0
        self.violations: list[str] = []

    def _event(self, status: str, operation: str, **metadata: Any) -> None:
        if self.trace is not None:
            self.trace.emit(
                "POLICY_CHECK",
                status=status,
                metadata={"group": self.policy.group, "operation": operation, **metadata},
            )

    def _deny(self, message: str, operation: str) -> None:
        self.violations.append(message)
        self._event("DENIED", operation, violation=message)
        if self.trace is not None:
            self.trace.emit("ERROR", status="FAILED", error_message=message, metadata={
                "error_type": "policy_violation", "group": self.policy.group, "operation": operation,
            })
        raise PolicyViolation(message)

    def before_model_call(self, tools: Iterable[dict[str, Any]] | None) -> None:
        if self.model_calls >= self.policy.max_model_calls:
            self._deny("model call budget exceeded", "model_call")
        tool_names = []
        for item in tools or ():
            function = item.get("function", item)
            name = function.get("name") if isinstance(function, dict) else None
            if name:
                tool_names.append(str(name))
        if tool_names and not self.policy.allowed_tools:
            self._deny("tools are forbidden for this experiment group", "model_call")
        unauthorized = sorted(set(tool_names) - set(self.policy.allowed_tools))
        if unauthorized:
            self._deny(f"unauthorized tools requested: {unauthorized}", "model_call")
        self.model_calls += 1
        self._event("ALLOWED", "model_call", call_index=self.model_calls, tools=tool_names)

    def validate_provider(self, provider: Any) -> None:
        configured_retries = int(getattr(provider, "max_retries", 0) or 0)
        if configured_retries > self.policy.max_transport_retries:
            self._deny(
                f"provider is configured for {configured_retries} transport retries; group allows {self.policy.max_transport_retries}",
                "provider_configuration",
            )

    def after_model_response(self, response: Any) -> None:
        attempts = int(getattr(response, "metadata", {}).get("attempt", 1) or 1)
        if attempts > self.policy.max_transport_retries + 1:
            self._deny(
                f"provider used {attempts - 1} transport retries; group allows {self.policy.max_transport_retries}",
                "provider_retry",
            )
        tool_calls = getattr(response, "tool_calls", []) or []
        names = []
        for item in tool_calls:
            function = item.get("function", item)
            if isinstance(function, dict) and function.get("name"):
                names.append(str(function["name"]))
        unauthorized = sorted(set(names) - set(self.policy.allowed_tools))
        if unauthorized:
            self._deny(f"model returned unauthorized tools: {unauthorized}", "model_response")

    def before_tool_call(self, tool_name: str, *, compute: bool = False) -> None:
        if tool_name not in self.policy.allowed_tools:
            self._deny(f"tool is not permitted: {tool_name}", "tool_call")
        if compute and self.compute_steps >= self.policy.max_compute_steps:
            self._deny("computation budget exceeded", "compute")
        if self.tool_calls >= self.policy.max_tool_calls:
            self._deny("tool call budget exceeded", "tool_call")
        self.tool_calls += 1
        if compute:
            self.compute_steps += 1
        self._event("ALLOWED", "tool_call", tool_name=tool_name, tool_index=self.tool_calls, compute=compute)

    def store_memory(self) -> None:
        if not self.policy.allow_memory:
            self._deny("memory is forbidden for this experiment group", "memory")
        if self.memory_items >= self.policy.memory_items:
            self._deny("run-local memory budget exceeded", "memory")
        self.memory_items += 1
        self._event("ALLOWED", "memory", memory_items=self.memory_items)

    def retrieval(self, source: str) -> None:
        if not self.policy.allow_retrieval:
            self._deny(f"retrieval is forbidden: {source}", "retrieval")
        self._event("ALLOWED", "retrieval", source=source)

    def snapshot(self) -> dict[str, Any]:
        return {
            "policy": self.policy.as_dict(),
            "used": {
                "model_calls": self.model_calls,
                "tool_calls": self.tool_calls,
                "compute_steps": self.compute_steps,
                "memory_items": self.memory_items,
            },
            "violations": list(self.violations),
        }


class PolicyProvider:
    """Provider decorator that makes group permissions executable."""

    def __init__(self, provider: Any, controller: PolicyController):
        self.provider = provider
        self.controller = controller
        self.model_name = getattr(provider, "model_name", "unknown")
        self.controller.validate_provider(provider)

    def complete(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None) -> Any:
        self.controller.before_model_call(tools)
        try:
            response = self.provider.complete(messages, tools=tools)
            self.controller.after_model_response(response)
            return response
        except PolicyViolation:
            raise

    def audit_trace(self) -> list[dict[str, Any]]:
        return self.provider.audit_trace()


class BoundedMemory:
    """Run-local memory; it cannot read files, network sources, or prior runs."""

    def __init__(self, controller: PolicyController):
        self.controller = controller
        self._items: list[dict[str, Any]] = []

    def write(self, item: dict[str, Any]) -> None:
        self.controller.store_memory()
        self._items.append(dict(item))

    def read(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._items]
