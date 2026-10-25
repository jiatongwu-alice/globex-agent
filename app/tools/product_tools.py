import requests
from app.guardrails import apply_search_constraints

BASE_URL = "https://dummyjson.com/products"



def search_products(
    query: str,
    max_price: float | None = None,
    limit: int = 5
    ) -> str:
    """Search products using a short keyword and optional filters.

    Args:
        query: A short product keyword, such as laptop or phone.
            Do not include price limits or full sentences.
        max_price: Maximum product price in USD.
        limit: Maximum number of products to return.
    """
    max_price, limit = apply_search_constraints(
    max_price,
    limit
    )

    print(
        f"[DEBUG] query={query}, "
        f"max_price={max_price}, limit={limit}"
    )

    try:

        response = requests.get(
            f"{BASE_URL}/search",
            params={"q": query, "limit": 0},
            timeout=10
        )

        response.raise_for_status()

        data = response.json()
        products = data["products"]
    except requests.Timeout:
        return "TOOL_ERROR: Product search timed out."
    except requests.HTTPError as e:
        status = (
            e.response.status_code
            if e.response is not None
            else "unknown")
        return f"TOOL_ERROR: Search API returned HTTP {status}."

    except requests.RequestException:
        return "TOOL_ERROR: Product search service unavailable."

    # Filter products by price
    if max_price is not None:
        products = [
            product for product in products
            if product["price"] <= max_price
        ]

    # Limit the number of products
    products = products[:max(1, min(limit, 20))]

    if not products:
        return "No matching products found."

    # Format the results
    result = []

    for product in products:
        result.append(
            f"ID: {product['id']}, "
            f"Name: {product['title']}, "
            f"Category: {product['category']}, "
            f"Price: ${product['price']}"
        )

    return "\n".join(result)


def get_product_details(product_id:str) -> str:
    """Get detailed information about a product.

    Args:
        product_id: The unique ID of the product.
    """

    print(f"[TOOL] Getting product details: {product_id}")

    try:

        response = requests.get(
            f"{BASE_URL}/{product_id}",
            timeout=10
        )

        response.raise_for_status()

        product = response.json()
    except requests.Timeout:
        return "TOOL_ERROR: Product details request timed out."

    except requests.HTTPError as e:
        if (
        e.response is not None
        and e.response.status_code == 404
    ):
            return f"TOOL_ERROR: Product ID {product_id} not found."

        return "TOOL_ERROR: Product details API returned an HTTP error."

    except requests.RequestException:
        return "TOOL_ERROR: Product details service unavailable."

    return (
        f"ID: {product['id']}\n"
        f"Name: {product['title']}\n"
        f"Price: ${product['price']}\n"
        f"Category: {product['category']}\n"
        f"Brand: {product.get('brand', 'Unknown')}\n"
        f"Description: {product.get('description', '')}"
    )


if __name__ == "__main__":
    products = search_products("phone")
    print(products)