/* ERPNext API adapter for CNCLeaders shop SPA */
(function (window) {
	"use strict";

	function call(method, args) {
		return new Promise(function (resolve, reject) {
			if (!window.frappe || !frappe.call) {
				reject(new Error("Frappe not loaded"));
				return;
			}
			frappe.call({
				method: method,
				args: args || {},
				callback: function (r) {
					if (r.exc) {
						reject(r.exc);
					} else {
						resolve(r.message);
					}
				},
				error: reject,
			});
		});
	}

	window.ShopAPI = {
		boot: function () {
			return call("custom_webshop.api.shop.get_shop_context");
		},
		getHomeData: function () {
			return call("custom_webshop.api.shop.get_home_data");
		},
		getCategories: function () {
			return call("custom_webshop.api.shop.get_categories");
		},
		getProducts: function (queryArgs) {
			return call("custom_webshop.api.shop.get_products", { query_args: queryArgs || {} });
		},
		getProductDetail: function (itemCode) {
			return call("custom_webshop.api.shop.get_product_detail", { item_code: itemCode });
		},
		getCart: function () {
			return call("custom_webshop.api.shop.get_cart_json");
		},
		updateCart: function (itemCode, qty, additionalNotes) {
			return call("custom_webshop.webshop.shopping_cart.cart.update_cart", {
				item_code: itemCode,
				qty: qty,
				additional_notes: additionalNotes || undefined,
				with_items: 1,
			}).catch(function () {
				return call("custom_webshop.shopping_cart.cart_override.update_cart", {
					item_code: itemCode,
					qty: qty,
					additional_notes: additionalNotes || undefined,
					with_items: 1,
				});
			});
		},
		addCustomerInfo: function (addressData, contactData) {
			return call("custom_webshop.shopping_cart.cart_override.add_customer_info", {
				address_data: JSON.stringify(addressData),
				contact_data: JSON.stringify(contactData),
			});
		},
		getCustomerAddresses: function () {
			return call(
				"custom_webshop.shopping_cart.cart_override.get_customer_addresses_with_contacts"
			);
		},
		updateCustomerInfo: function (addressName, contactName, addressData, contactData) {
			return call("custom_webshop.shopping_cart.cart_override.update_customer_info", {
				address_name: addressName,
				address_data: JSON.stringify(addressData),
				contact_name: contactName,
				contact_data: JSON.stringify(contactData),
			});
		},
		updateCartAddress: function (addressName) {
			return call("custom_webshop.shopping_cart.cart_override.update_cart_address", {
				address_type: "Shipping",
				address_name: addressName,
			});
		},
		getGovernorates: function () {
			return call("custom_webshop.shopping_cart.shipping_api.get_governorates");
		},
		getShippingRules: function () {
			return call("custom_webshop.shopping_cart.shipping_api.get_governorate_shipping_rules");
		},
		updateCartShipping: function (shippingRule, shippingDestination) {
			return call("custom_webshop.shopping_cart.shipping_api.update_cart_shipping", {
				shipping_rule: shippingRule,
				shipping_destination: shippingDestination,
			});
		},
		getPaymentPreview: function () {
			return call("custom_webshop.api.shop.get_payment_preview");
		},
		prepareCheckout: function () {
			return call("webshop.webshop.shopping_cart.cart.place_order");
		},
		getOrders: function () {
			return call("custom_webshop.api.shop.get_orders_json");
		},
		getOrderForPayment: function (orderId) {
			return call("custom_webshop.api.shop.get_order_for_payment", { order_id: orderId });
		},
		confirmPayment: function (paymentMethod, filename, fileContent, orderId) {
			return call("custom_webshop.api.payment.confirm_payment", {
				payment_method: paymentMethod,
				filename: filename,
				file_content: fileContent,
				order_id: orderId || undefined,
			});
		},
		signUp: function (email, fullName, pwd, mobileNo) {
			return call("custom_webshop.api.auth.custom_sign_up", {
				email: email,
				full_name: fullName,
				pwd: pwd,
				mobile_no: mobileNo,
				redirect_to: "/shop",
			});
		},
		login: function (email, pwd) {
			return new Promise(function (resolve, reject) {
				if (!window.frappe || !frappe.call) {
					reject(new Error("Frappe not loaded"));
					return;
				}
				frappe.call({
					type: "POST",
					method: "login",
					args: { usr: email, pwd: pwd },
					callback: function (r) {
						if (r.message === "Logged In") {
							resolve(r);
						} else {
							reject(r);
						}
					},
					error: reject,
				});
			});
		},
		logout: function () {
			return call("logout");
		},
		admin: {
			getAnalytics: function () {
				return call("custom_webshop.api.admin.get_analytics");
			},
			getInventory: function () {
				return call("custom_webshop.api.admin.get_inventory");
			},
			getPendingOrders: function () {
				return call("custom_webshop.api.admin.get_pending_orders");
			},
			approveOrder: function (orderId) {
				return call("custom_webshop.api.admin.approve_order", { order_id: orderId });
			},
			rejectOrder: function (orderId, reason) {
				return call("custom_webshop.api.admin.reject_order", {
					order_id: orderId,
					reason: reason,
				});
			},
			getSlides: function () {
				return call("custom_webshop.api.admin.get_slides");
			},
			saveSlide: function (slideData) {
				return call("custom_webshop.api.admin.save_slide", { slide_data: JSON.stringify(slideData) });
			},
			deleteSlide: function (slideId) {
				return call("custom_webshop.api.admin.delete_slide", { slide_id: slideId });
			},
		},
	};

	// Fix update_cart method path - use override directly
	ShopAPI.updateCart = function (itemCode, qty, additionalNotes) {
		return call("custom_webshop.shopping_cart.cart_override.update_cart", {
			item_code: itemCode,
			qty: qty,
			additional_notes: additionalNotes || undefined,
			with_items: 1,
		});
	};

	ShopAPI.placeOrder = ShopAPI.prepareCheckout;
})(window);
