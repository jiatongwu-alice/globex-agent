
from unittest.mock import patch
import requests
from app.tools.product_tools import search_products


def test_search_timeout():

    # Simulate a timeout error
    with patch(
        "app.tools.product_tools.requests.get",
        side_effect=requests.Timeout("Simulated timeout")
    ):
        result = search_products("laptop")

    # Check whether our tool handles the error correctly
    assert result == "TOOL_ERROR: Product search timed out."


from app.tools.product_tools import get_product_details


def test_product_not_found():
    # Create a fake HTTP response
    mock_response = requests.Response()
    mock_response.status_code = 404

    with patch(
        "app.tools.product_tools.requests.get",
        return_value=mock_response
    ):
        result = get_product_details(999999)

    assert result == "TOOL_ERROR: Product ID 999999 not found."

