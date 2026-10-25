
import re

from dataclasses import dataclass
from contextvars import ContextVar
from contextlib import contextmanager

#Save user requirements
@dataclass(frozen=True)
class TaskConstraints:
    max_price: float | None = None
    max_items: int | None = None

#Record the number of times the current task has been delegated to a Research Agent.
@dataclass
class ExecutionState:
    """Track research delegations within one user request."""

    research_calls: int = 0
    max_research_calls: int = 1


_active_execution = ContextVar(
    "task_execution",
    default=None
)



# Store constraints for the current execution context
_active_constraints = ContextVar(
    "task_constraints",
    default=None
)


def extract_constraints(text: str) -> TaskConstraints:
    """Extract simple budget and quantity constraints."""

    budget_match = re.search(
        r"\b(?:under|below|less than)\s*\$\s*([\d,]+)",
        text,
        re.IGNORECASE
    )

    quantity_match = re.search(
        r"\b(?:exactly|up to)\s+(one|two|three|\d+)\b",
        text,
        re.IGNORECASE
    )

    max_price = (
        float(budget_match.group(1).replace(",", ""))
        if budget_match else None
    )

    numbers = {"one": 1, "two": 2, "three": 3}

    max_items = None

    if quantity_match:
        value = quantity_match.group(1).lower()
        max_items = numbers.get(value, None)

        if max_items is None:
            max_items = int(value)

    return TaskConstraints(
        max_price=max_price,
        max_items=max_items
    )



@contextmanager
def use_task_constraints(constraints: TaskConstraints):
    """Manage constraints and execution state for one request."""

    constraint_token = _active_constraints.set(constraints)

    execution_token = _active_execution.set(
        ExecutionState()
    )

    try:
        yield
    finally:
        _active_execution.reset(execution_token)
        _active_constraints.reset(constraint_token)



def apply_search_constraints(
    max_price: float | None,
    limit: int
) -> tuple[float | None, int]:
    """Prevent tool parameters from exceeding active limits."""

    if limit < 1:
        raise ValueError("Search limit must be positive.")

    constraints = _active_constraints.get()

    if constraints is not None:

        if constraints.max_price is not None:
            max_price = (
                min(max_price, constraints.max_price)
                if max_price is not None
                else constraints.max_price
            )

        if constraints.max_items is not None:
            limit = min(limit, constraints.max_items)

    return max_price, limit


def claim_research_call() -> bool:
    """Allow at most one research delegation per request."""

    state = _active_execution.get()

    # Allow standalone calls outside a managed request
    if state is None:
        return True

    if state.research_calls >= state.max_research_calls:
        return False

    state.research_calls += 1
    return True

