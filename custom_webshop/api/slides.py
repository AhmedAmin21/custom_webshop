"""
Hero Slideshow API — backed by Website Slideshow doctype.

The shop page uses a single Website Slideshow named "CNCLeaders Hero".
This module provides guest-accessible read and manager-restricted write endpoints.
"""

import frappe
from frappe import _

SLIDESHOW_NAME = "CNCLeaders Hero"


@frappe.whitelist()
def is_slide_admin():
	"""Return True if the current user may manage hero slides."""
	if frappe.session.user == "Guest":
		return False
	roles = frappe.get_roles()
	return "System Manager" in roles or "Website Manager" in roles


def _get_or_create_slideshow():
    """Return the hero slideshow doc, creating it if absent."""
    if not frappe.db.exists("Website Slideshow", SLIDESHOW_NAME):
        doc = frappe.new_doc("Website Slideshow")
        doc.slideshow_name = SLIDESHOW_NAME
        doc.flags.ignore_permissions = True
        doc.insert()
        frappe.db.commit()
    return frappe.get_doc("Website Slideshow", SLIDESHOW_NAME)


@frappe.whitelist(allow_guest=True)
def get_slides():
    """
    Return the list of hero slides as plain dicts.
    Each dict has: eyebrow, title, subtitle, link, image, idx (sort order).
    """
    if not frappe.db.exists("Website Slideshow", SLIDESHOW_NAME):
        return []

    doc = frappe.get_doc("Website Slideshow", SLIDESHOW_NAME)
    result = []
    for item in sorted(doc.slideshow_items or [], key=lambda x: x.idx):
        result.append({
            "name": item.name,
            "idx": item.idx,
            "image": item.image or "",
            "title": item.heading or "",
            "eyebrow": item.description or "",
            "subtitle": item.url or "",  # We repurpose the url field as subtitle storage
            "link": item.get("item_link") or "/catalog",
        })
    return result


@frappe.whitelist()
def save_slide(eyebrow, title, subtitle, link="/catalog", image="", slide_name=None):
    """
    Insert or update a single hero slide.
    Requires System Manager role.
    """
    frappe.only_for("System Manager")

    doc = _get_or_create_slideshow()

    if slide_name:
        # Update existing slide row
        for item in doc.slideshow_items:
            if item.name == slide_name:
                item.heading = title
                item.description = eyebrow
                item.url = subtitle
                item.image = image
                # item_link is a custom field we add if it exists, fallback to url
                if hasattr(item, "item_link"):
                    item.item_link = link
                break
    else:
        # Append new slide
        new_item = {
            "image": image,
            "heading": title,
            "description": eyebrow,
            "url": subtitle,
        }
        if hasattr(doc, "slideshow_items") and doc.slideshow_items:
            # Check if item_link field exists on child doctype
            sample = doc.slideshow_items[0]
            if hasattr(sample, "item_link"):
                new_item["item_link"] = link
        doc.append("slideshow_items", new_item)

    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"success": True, "message": _("Slide saved.")}


@frappe.whitelist()
def delete_slide(slide_name):
    """
    Remove a slide row from the hero slideshow.
    Requires System Manager role.
    """
    frappe.only_for("System Manager")

    doc = _get_or_create_slideshow()
    doc.slideshow_items = [item for item in doc.slideshow_items if item.name != slide_name]
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"success": True, "message": _("Slide deleted.")}


@frappe.whitelist()
def reorder_slides(slide_names):
    """
    Reorder slides by providing an ordered list of row names.
    Requires System Manager role.
    slide_names: JSON list of row names in desired order.
    """
    import json
    frappe.only_for("System Manager")

    if isinstance(slide_names, str):
        slide_names = json.loads(slide_names)

    doc = _get_or_create_slideshow()
    order_map = {name: idx for idx, name in enumerate(slide_names)}

    for item in doc.slideshow_items:
        if item.name in order_map:
            item.idx = order_map[item.name] + 1

    doc.slideshow_items.sort(key=lambda x: x.idx)
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"success": True, "message": _("Slides reordered.")}
