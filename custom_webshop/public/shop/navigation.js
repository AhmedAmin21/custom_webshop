/* Path-based navigation helpers for CNCLeaders shop */
(function () {
	"use strict";

	function buildQuery(params) {
		if (!params) return "";
		const search = new URLSearchParams(params).toString();
		return search ? "?" + search : "";
	}

	window.ShopNav = {
		home: function () {
			return "/shop";
		},
		catalog: function (params) {
			return "/shop/catalog" + buildQuery(params);
		},
		product: function (itemCode) {
			return "/shop/product/" + encodeURIComponent(itemCode);
		},
		cart: function () {
			return "/shop/cart";
		},
		payment: function (orderId) {
			return orderId
				? "/shop/payment?order_id=" + encodeURIComponent(orderId)
				: "/shop/payment";
		},
		orders: function () {
			return "/shop/orders";
		},
		admin: function () {
			return "/shop/admin";
		},
		login: function (redirect) {
			return redirect
				? "/shop/login?redirect-to=" + encodeURIComponent(redirect)
				: "/shop/login";
		},
		signup: function () {
			return "/shop/signup";
		},
		go: function (path) {
			window.location.href = path;
		},
	};

	/** Redirect legacy hash URLs to path-based routes (one-time on load). */
	window.redirectLegacyHash = function () {
		const hash = window.location.hash;
		if (!hash || hash.length < 2) return false;

		const raw = hash.slice(1);
		const view = raw.split("?")[0];
		const params = new URLSearchParams(raw.split("?")[1] || "");

		const map = {
			home: ShopNav.home(),
			catalog: ShopNav.catalog(Object.fromEntries(params.entries())),
			cart: ShopNav.cart(),
			payment: ShopNav.payment(params.get("order_id")),
			orders: ShopNav.orders(),
			admin: ShopNav.admin(),
			login: ShopNav.login(),
			signup: ShopNav.signup(),
		};

		if (view === "detail") {
			const id = params.get("id");
			if (id) {
				window.location.replace(ShopNav.product(id));
				return true;
			}
		}

		if (map[view]) {
			window.location.replace(map[view]);
			return true;
		}
		return false;
	};
})();
