/**
 * Legacy storefront stub — redirects to the ERP-integrated /shop SPA.
 * Do not use this file for production checkout or catalog logic.
 */
(function () {
	if (!window.location.pathname.startsWith("/shop")) {
		window.location.replace("/shop" + window.location.pathname.replace(/^\//, ""));
	}
})();
