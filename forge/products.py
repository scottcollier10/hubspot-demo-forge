"""Product and line item seeding."""

import random


def seed_products(client, products: list[dict], forge_source: str = "") -> dict[str, str]:
    """Create products in HubSpot. Returns {product_name: hubspot_id} map."""
    print("\n-- Products " + "-" * 43)
    created = 0
    product_id_map = {}

    for product in products:
        props = {**product}
        if forge_source:
            props["forge_source"] = forge_source
        payload = {"properties": props}
        result, status = client.post("/crm/v3/objects/products", payload)

        if status in (200, 201):
            product_id_map[product["name"]] = result["id"]
            created += 1
            print(f"  created: {product['name']} (${product.get('price', '?')})")
        else:
            print(f"  ERROR {status}: {product['name']}")

        client.throttle()

    print(f"  --- {created} products created")
    return product_id_map


def seed_line_items(
    client,
    deal_records: list[dict],
    product_id_map: dict[str, str],
    products: list[dict],
    line_items_per_deal: list[int],
) -> int:
    """Create line items linking products to deals."""
    print("\n-- Line Items " + "-" * 41)
    created = 0
    lo, hi = line_items_per_deal
    product_names = list(product_id_map.keys())

    if not product_names:
        print("  No products to attach")
        return 0

    for deal in deal_records:
        count = random.randint(lo, hi)
        selected = random.sample(product_names, min(count, len(product_names)))

        for pname in selected:
            product = next((p for p in products if p["name"] == pname), {})
            props = {
                "name": pname,
                "price": product.get("price", "10000"),
                "quantity": "1",
                "hs_product_id": product_id_map[pname],
            }
            result, status = client.post("/crm/v3/objects/line_items", {"properties": props})

            if status in (200, 201):
                li_id = result["id"]
                client.put(
                    f"/crm/v4/objects/line_items/{li_id}/associations/default/deals/{deal['id']}"
                )
                created += 1
            client.throttle()

    print(f"  --- {created} line items created")
    return created
