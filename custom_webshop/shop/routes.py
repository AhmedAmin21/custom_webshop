"""Central URL helpers for the /shop storefront."""

SHOP_BASE = "/shop"


def shop_url(path: str = "") -> str:
	"""Build a storefront URL under /shop."""
	path = (path or "").strip("/")
	return f"{SHOP_BASE}/{path}" if path else SHOP_BASE
