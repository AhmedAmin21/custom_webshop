(function () {
	"use strict";

	window.CNCShop = window.CNCShop || {};

	CNCShop.showToast = function (message, type) {
		const container = document.getElementById("toast-container");
		if (!container) return;
		const toast = document.createElement("div");
		toast.className = "toast toast-" + (type || "info");
		toast.textContent = message;
		container.appendChild(toast);
		setTimeout(function () { toast.remove(); }, 3500);
	};

	CNCShop.initTheme = function () {
		const btn = document.getElementById("theme-btn");
		if (!btn) return;
		const saved = localStorage.getItem("cnc_theme");
		if (saved === "dark") document.body.classList.add("dark-theme");
		btn.addEventListener("click", function () {
			document.body.classList.toggle("dark-theme");
			localStorage.setItem("cnc_theme", document.body.classList.contains("dark-theme") ? "dark" : "light");
		});
	};

	CNCShop.initCartDrawer = function () {
		const drawer = document.getElementById("cart-drawer");
		const overlay = document.getElementById("cart-drawer-overlay");
		const toggle = document.getElementById("cart-toggle-btn");
		const closeBtn = document.getElementById("close-drawer-btn");
		if (!drawer) return;

		function open() { drawer.classList.add("active"); overlay && overlay.classList.add("active"); }
		function close() { drawer.classList.remove("active"); overlay && overlay.classList.remove("active"); }

		toggle && toggle.addEventListener("click", open);
		closeBtn && closeBtn.addEventListener("click", close);
		overlay && overlay.addEventListener("click", close);
	};

	CNCShop.initMobileMenu = function () {
		const btn = document.getElementById("mobile-menu-btn");
		const links = document.querySelector(".nav-links");
		if (!btn || !links) return;
		btn.addEventListener("click", function () {
			links.classList.toggle("mobile-open");
		});
	};

	CNCShop.updateCartBadge = function () {
		const badge = document.getElementById("cart-badge");
		if (!badge || !window.frappe) return;
		const count = frappe.get_cookie("cart_count") || 0;
		badge.textContent = count;
		badge.style.display = count > 0 ? "flex" : "none";
	};

	document.addEventListener("DOMContentLoaded", function () {
		CNCShop.initTheme();
		CNCShop.initCartDrawer();
		CNCShop.initMobileMenu();
		if (window.frappe && frappe.ready) {
			frappe.ready(CNCShop.updateCartBadge);
		}
	});
})();
