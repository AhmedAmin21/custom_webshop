import frappe
from frappe import _
from frappe.utils import flt

from webshop.webshop.shopping_cart.cart import (
    _get_cart_quotation,
    get_party,
    get_cart_quotation,
    set_cart_count,
)
from webshop.webshop.doctype.webshop_settings.webshop_settings import (
    get_shopping_cart_settings,
)
from custom_shipping_rule.utils.shipping_utils import get_governorate_shipping_amount


def apply_cart_settings_for_webshop(party=None, quotation=None):
    """
    Replicates webshop's apply_cart_settings but SKIPS _apply_shipping_rule
    so non-Governorate rules are never auto-selected.
    """
    if not party:
        party = get_party()
    if not quotation:
        quotation = _get_cart_quotation(party)

    cart_settings = frappe.get_cached_doc("Webshop Settings")

    # 1. Price list & rate
    from webshop.webshop.shopping_cart.cart import set_price_list_and_rate
    set_price_list_and_rate(quotation, cart_settings)

    # 2. Calculate totals
    quotation.run_method("calculate_taxes_and_totals")

    # 3. Set taxes
    from webshop.webshop.shopping_cart.cart import set_taxes
    set_taxes(quotation, cart_settings)

    # 4. Governorate shipping ONLY (never auto-select non-Governorate)
    if quotation.shipping_rule:
        is_governorate = frappe.db.get_value(
            "Shipping Rule", quotation.shipping_rule, "calculate_based_on"
        ) == "Governorate"
        if is_governorate and quotation.shipping_destination:
            quotation.run_method("apply_shipping_rule")
            quotation.run_method("calculate_taxes_and_totals")
        elif not is_governorate:
            # Non-Governorate rule slipped in — clear it
            quotation.shipping_rule = None
            quotation.shipping_destination = None


@frappe.whitelist()
def get_governorate_shipping_rules():
    """
    Return active shipping rules where calculate_based_on == 'Governorate'.
    """
    rules = frappe.get_all(
        "Shipping Rule",
        filters={
            "calculate_based_on": "Governorate",
            "disabled": 0,
            "shipping_rule_type": "Selling",
        },
        fields=["name", "label"],
        order_by="label",
    )
    return [[rule.name, rule.label or rule.name] for rule in rules]


def _get_cart_weight_info(quotation=None):
    """
    Return raw total weight and UOM from the quotation.
    Does NOT convert — returns exactly what is stored.
    """
    if quotation is None:
        quotation = _get_cart_quotation()

    total_weight = flt(quotation.total_net_weight)

    # Determine weight UOM
    weight_uom = None
    if quotation.get("weight_uom"):
        weight_uom = quotation.weight_uom
    elif quotation.get("items"):
        for item in quotation.items:
            if item.get("weight_uom"):
                weight_uom = item.weight_uom
                break

    return {
        "total_weight": total_weight,
        "weight_uom": weight_uom or "",
    }


@frappe.whitelist()
def get_cart_total_weight():
    """
    Return total weight and its UOM for the current cart.
    """
    return _get_cart_weight_info()


@frappe.whitelist()
def get_shipping_amount_for_cart(shipping_rule, governorate, weight):
    """
    Calculate shipping amount for a given shipping rule, governorate, and weight.
    """
    weight = flt(weight)
    shipping_rule_doc = frappe.get_doc("Shipping Rule", shipping_rule)

    amount = get_governorate_shipping_amount(shipping_rule, governorate, weight)
    return flt(amount, 2)


@frappe.whitelist()
def update_cart_shipping(shipping_rule=None, shipping_destination=None):
    """
    Update the cart quotation with shipping rule and destination,
    apply the shipping rule, and recalculate totals.
    Returns the updated cart context for re-rendering.
    """
    quotation = _get_cart_quotation()

    if shipping_rule:
        quotation.shipping_rule = shipping_rule
    if shipping_destination is not None:
        quotation.shipping_destination = shipping_destination

    # Use our custom cart settings that never auto-select non-Governorate rules
    apply_cart_settings_for_webshop(quotation=quotation)

    quotation.flags.ignore_permissions = True
    quotation.save()

    return get_cart_quotation(quotation)


@frappe.whitelist()
def get_governorates():
    """
    Return list of enabled governorates.
    """
    return frappe.get_all(
        "Governorate",
        filters={"enabled": 1},
        fields=["name", "governorate_name"],
        order_by="governorate_name",
    )


def _get_weight_conversion_factor(weight_uom):
    """Get conversion factor to Kg for a given weight UOM."""
    conversion_factor = frappe.db.get_value(
        "UOM Conversion Factor",
        {"category": "Mass", "from_uom": weight_uom, "to_uom": "Kg"},
        "value"
    )
    if conversion_factor:
        return flt(conversion_factor)

    # Common fallbacks
    weight_uom_lower = weight_uom.lower()
    if weight_uom_lower in ("gram", "grams", "g"):
        return 0.001
    elif weight_uom_lower in ("ton", "tons", "tonne", "tonnes"):
        return 1000
    elif weight_uom_lower in ("pound", "pounds", "lb", "lbs"):
        return 0.453592
    elif weight_uom_lower in ("ounce", "ounces", "oz"):
        return 0.0283495

    return None
