(function () {
	"use strict";

	window.CNCShop = window.CNCShop || {};

	const TRANSLATIONS = {
		en: { nav_home: "Home", nav_catalog: "All Products", nav_orders: "Track Orders" },
		ar: { nav_home: "الرئيسية", nav_catalog: "كل المنتجات", nav_orders: "تتبع الطلبات" },
	};

	CNCShop.lang = localStorage.getItem("cnc_lang_v2") || "ar";

	CNCShop.applyLanguage = function (lang) {
		CNCShop.lang = lang;
		localStorage.setItem("cnc_lang_v2", lang);
		document.documentElement.lang = lang;
		document.body.classList.toggle("rtl", lang === "ar");
		const dict = TRANSLATIONS[lang] || TRANSLATIONS.en;
		document.querySelectorAll("[data-i18n]").forEach(function (el) {
			const key = el.getAttribute("data-i18n");
			if (dict[key]) el.textContent = dict[key];
		});
		const btnText = document.getElementById("lang-btn-text");
		if (btnText) btnText.textContent = lang === "ar" ? "AR" : "EN";
	};

	document.addEventListener("DOMContentLoaded", function () {
		CNCShop.applyLanguage(CNCShop.lang);
		const langBtn = document.getElementById("lang-btn");
		if (langBtn) {
			langBtn.addEventListener("click", function () {
				CNCShop.applyLanguage(CNCShop.lang === "en" ? "ar" : "en");
			});
		}
	});
})();
