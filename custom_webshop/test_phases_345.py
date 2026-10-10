def run_tests():
    print("Testing Phase 3 - Cart Quotation")
    from custom_webshop.shopping_cart.cart_override import get_cart_quotation
    try:
        cart = get_cart_quotation()
        print("Cart fetch success. Keys:", cart.keys())
    except Exception as e:
        print("Cart fetch failed:", e)

    print("\nTesting Phase 4 - Catalog Caches")
    from custom_webshop.api.catalog import get_tool_families, get_materials, get_item_attributes, get_catalog_products
    try:
        families = get_tool_families()
        print(f"Tool families count: {len(families)}")
        materials = get_materials()
        print(f"Materials count: {len(materials)}")
        attrs = get_item_attributes()
        print(f"Attributes count: {len(attrs)}")
        
        # Test catalog products
        products = get_catalog_products()
        print(f"Catalog products fetched successfully. Return type: {type(products)}")
    except Exception as e:
        print("Catalog cache fetch failed:", e)

    print("\nTesting Phase 5 - Product Page Waterfall")
    from custom_webshop.api.catalog import get_full_product_page_data
    import frappe
    try:
        item_code = frappe.db.get_value("Website Item", {"published": 1}, "item_code")
        if item_code:
            data = get_full_product_page_data(item_code)
            print(f"Product data fetch success for {item_code}. Keys:", data.keys())
        else:
            print("No published website items found to test.")
    except Exception as e:
        print("Product page fetch failed:", e)
