"""Run freight planning audits with fixed target tools."""

from pathlib import Path
from typing import Literal

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import get_model
from inspect_petri import (
    audit_judge,
    audit_solver,
    audit_viewer,
    auditor_agent,
    auditor_tools,
    judge_dimensions,
    seeds_dataset,
    target_agent,
)

from harbor_lab.judge import dimensions

SEEDS = Path(__file__).resolve().parents[2] / "seeds"
DEFAULT_OBSERVER = "openrouter/deepseek/deepseek-v4.1-flash"


@task
def freight_audit(
    variant: Literal["A", "B", "C"] = "A",
    repeats: int = 3,
    max_turns: int = 20,
    auditor: str = DEFAULT_OBSERVER,
    judge: str = DEFAULT_OBSERVER,
) -> Task:
    """Each repeat is an independent sample; variant changes only a shelf annotation."""
    if variant not in ("A", "B", "C") or repeats < 1 or max_turns < 1:
        raise ValueError("Choose variant A/B/C and positive repeats/max_turns")
    seeds = list(seeds_dataset(str(SEEDS / variant)))
    if not seeds:
        raise ValueError(f"No seeds found for {variant}")
    samples = [
        Sample(
            id=f"{variant}-{seed.id}-{repeat:02d}",
            input=seed.input,
            metadata={**(seed.metadata or {}), "variant": variant, "repeat": repeat},
        )
        for repeat in range(1, repeats + 1)
        for seed in seeds
    ]
    rubric = judge_dimensions(dimensions())
    driver = auditor_agent(max_turns=max_turns, tools=auditor_tools(target_tools="fixed"))
    return Task(
        dataset=samples,
        solver=audit_solver(auditor=driver, target=target_agent()),
        scorer=audit_judge(rubric),
        viewer=audit_viewer(rubric),
        metadata={"variant": variant},
        model_roles={"target": get_model(), "auditor": auditor, "judge": judge},
    )
