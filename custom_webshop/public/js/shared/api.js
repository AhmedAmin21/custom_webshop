(function () {
	"use strict";

	window.CNCShop = window.CNCShop || {};
	const base = (window.cnc_shop_routes && window.cnc_shop_routes.base) || "/shop";

	CNCShop.api = {
		updateCart: function (args, callback) {
			return frappe.call({
				method: "webshop.webshop.shopping_cart.cart.update_cart",
				args: args,
				callback: callback,
			});
		},
		confirmPayment: function (args, callback) {
			return frappe.call({
				method: "custom_webshop.api.payment.confirm_payment",
				args: args,
				callback: callback,
			});
		},
		cartUrl: base + "/cart",
		paymentUrl: function (orderId) {
			return base + "/payment?order_id=" + encodeURIComponent(orderId);
		},
		ordersUrl: base + "/orders",
	};
})();
