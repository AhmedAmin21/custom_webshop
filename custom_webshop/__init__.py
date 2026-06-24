__version__ = "0.0.1"

import sys

from custom_webshop import wishlist_shim

# Patch missing upstream webshop wishlist module used by ProductQuery stock checks
sys.modules.setdefault("webshop.templates.pages.wishlist", wishlist_shim)
