
from unittest.mock import patch, MagicMock

from app.guardrails import (
    TaskConstraints,
    extract_constraints,
    use_task_constraints,
    apply_search_constraints
)

from app.tools.product_tools import search_products

#Extract budget and quantity from common English requests
def test_extract_constraints():

    text = "Research exactly two laptops under $1500."

    result = extract_constraints(text)

    assert result.max_price == 1500
    assert result.max_items == 2

#Prevent product search tools from exceeding the allocated budget.
def test_budget_cannot_be_expanded():

    constraints = TaskConstraints(
        max_price=1500,
        max_items=2
    )

    with use_task_constraints(constraints):
        price, limit = apply_search_constraints(
            max_price=1750,
            limit=10
        )

    assert price == 1500
    assert limit == 2

#Limit the number of products returned in a single searchLimit the number of products returned in a single search
def test_missing_price_constraint_is_restored():

    constraints = TaskConstraints(max_price=1500)

    with use_task_constraints(constraints):
        price, limit = apply_search_constraints(
            max_price=None,
            limit=5
        )

    assert price == 1500
    assert limit == 5

#Preventing the carryover of constraints from different tasks
def test_constraints_reset_after_execution():

    with use_task_constraints(
        TaskConstraints(max_price=1500, max_items=2)
    ):
        apply_search_constraints(1750, 10)

    # The previous task must not affect another task
    price, limit = apply_search_constraints(1750, 10)

    assert price == 1750
    assert limit == 10


def test_search_tool_enforces_constraints():

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "products": [
            {
                "id": 1,
                "title": "Laptop A",
                "category": "laptops",
                "price": 1099
            },
            {
                "id": 2,
                "title": "Laptop B",
                "category": "laptops",
                "price": 1399
            },
            {
                "id": 3,
                "title": "Laptop C",
                "category": "laptops",
                "price": 1700
            }
        ]
    }

    with patch(
        "app.tools.product_tools.requests.get",
        return_value=fake_response
    ):
        with use_task_constraints(
            TaskConstraints(
                max_price=1500,
                max_items=2
            )
        ):
            result = search_products(
                query="laptop",
                max_price=1750,
                limit=10
            )

    assert "Laptop A" in result
    assert "Laptop B" in result
    assert "Laptop C" not in result
