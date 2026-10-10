__version__ = "0.0.1"

from custom_webshop.shopping_cart.stock import patch_webshop_stock_resolver
from custom_webshop.shopping_cart.party import patch_webshop_get_party

patch_webshop_stock_resolver()
patch_webshop_get_party()

