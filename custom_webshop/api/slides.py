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
    Requires System Manager or Website Manager role.
    """
    frappe.only_for(["System Manager", "Website Manager"])

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
    Requires System Manager or Website Manager role.
    """
    frappe.only_for(["System Manager", "Website Manager"])

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
    Requires System Manager or Website Manager role.
    slide_names: JSON list of row names in desired order.
    """
    import json
    frappe.only_for(["System Manager", "Website Manager"])

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


@frappe.whitelist()
def get_image_files(search=None, limit=60):
    """
    Return a list of available public image files from the File DocType.
    Requires slide admin permission.
    """
    if not is_slide_admin():
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif", ".avif")
    filters = {
        "is_folder": 0,
        "is_private": 0,
    }
    if search:
        filters["file_name"] = ["like", f"%{search}%"]

    files = frappe.get_all(
        "File",
        filters=filters,
        fields=["name", "file_name", "file_url", "creation"],
        order_by="creation desc",
        limit=int(limit) * 2 if limit else 100,
    )

    seen = set()
    result = []
    for f in files:
        url = (f.get("file_url") or "").strip()
        name = (f.get("file_name") or "").strip()
        if not url or url in seen:
            continue
        ext = url.lower().split("?")[0]
        if any(ext.endswith(e) for e in IMAGE_EXTS) or any(name.lower().endswith(e) for e in IMAGE_EXTS):
            seen.add(url)
            result.append({
                "name": f.name,
                "file_name": f.file_name or url.split("/")[-1],
                "file_url": url,
                "creation": str(f.creation),
            })
            if limit and len(result) >= int(limit):
                break

    return result


@frappe.whitelist()
def upload_slide_image(filename=None, file_content=None):
    """
    Upload an image file to be used in slides, stored as a public File record.
    Accepts base64 file_content + filename or standard multipart file from frappe.request.files.
    """
    import base64
    if not is_slide_admin():
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    content = None
    fname = None
    if file_content and filename:
        if "," in file_content:
            file_content = file_content.split(",", 1)[1]
        content = base64.b64decode(file_content)
        fname = filename
    elif hasattr(frappe.request, "files") and "file" in frappe.request.files:
        upload = frappe.request.files["file"]
        fname = upload.filename
        content = upload.read()
    else:
        frappe.throw(_("No file provided for upload."))

    IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif", ".avif")
    if not any(fname.lower().endswith(e) for e in IMAGE_EXTS):
        frappe.throw(_("Only image files ({0}) are allowed.").format(", ".join(IMAGE_EXTS)))

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "content": content,
        "is_private": 0,
        "attached_to_doctype": "Website Slideshow",
        "attached_to_name": SLIDESHOW_NAME,
    })
    file_doc.flags.ignore_permissions = True
    file_doc.insert()
    frappe.db.commit()

    return {
        "success": True,
        "file_url": file_doc.file_url,
        "file_name": file_doc.file_name,
        "name": file_doc.name,
    }

