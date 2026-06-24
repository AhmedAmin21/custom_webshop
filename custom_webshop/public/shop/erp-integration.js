/* Wire CNCLeaders SPA to ERPNext backend — loaded after app.js */
(function () {
	"use strict";

	window.shopState = window.shopState || {
		governorates: [],
		shippingRules: [],
		paymentOptions: window.SHOP_BOOT?.payment_options || [],
		currentPaymentOrder: null,
		catalogItems: [],
		catalogCount: 0,
		booted: false,
	};

	function formatMoney(amount, currency) {
		const sym = currency === "EGP" ? "EGP " : "$";
		return sym + parseFloat(amount || 0).toFixed(2);
	}

	function showApiError(err) {
		const msg =
			(typeof err === "string" && err) ||
			(err && err.message) ||
			"Something went wrong. Please try again.";
		if (typeof showToast === "function") showToast(msg, "info");
	}

	async function bootstrapShop() {
		try {
			const boot = await ShopAPI.boot();
			Object.assign(window.shopState, boot);
			window.shopState.booted = true;
			const page = window.SHOP_BOOT?.active_page || "home";

			if (boot.user_fullname) {
				const nameEl = document.getElementById("user-display-name");
				if (nameEl) nameEl.textContent = boot.user_fullname;
			}

			const adminLink = document.querySelector('.nav-link[data-view="admin"]');
			if (adminLink && !boot.is_admin) {
				adminLink.closest("li").style.display = "none";
			}

			if (page === "home" || page === "admin") {
				const homeData = await ShopAPI.getHomeData();
				if (homeData.products && homeData.products.length) {
					state.products = homeData.products;
				}
				if (homeData.slides && homeData.slides.length) {
					state.slides = homeData.slides;
				}
				if (homeData.categories) {
					Object.assign(CATEGORIES, homeData.categories);
				}
				if (homeData.category_descriptions) {
					Object.assign(CATEGORY_DESCRIPTIONS, homeData.category_descriptions);
				}
			}

			if (page === "home" || page === "catalog" || page === "admin") {
				const cats = await ShopAPI.getCategories();
				if (cats) Object.assign(CATEGORIES, cats);
			}

			await syncCartFromServer();
			updateCartBadgeCount();

			if (window.SHOP_BOOT?.user_fullname) {
				const el = document.getElementById("cust-name");
				if (el && !el.value) el.value = window.SHOP_BOOT.user_fullname;
			}

			if (typeof initCurrentPage === "function") {
				initCurrentPage();
			}
		} catch (e) {
			console.error("Shop bootstrap failed", e);
			if (typeof initCurrentPage === "function") {
				initCurrentPage();
			}
		}
	}

	async function syncCartFromServer() {
		try {
			const cart = await ShopAPI.getCart();
			state.cart = (cart.items || []).map(function (i) {
				return { productId: i.productId || i.item_code, qty: i.qty };
			});
			state._cartTotals = cart;
			(cart.items || []).forEach(function (i) {
				const id = i.productId || i.item_code;
				if (!id) return;
				const mapped = {
					id: id,
					name: i.name || id,
					price: i.price || 0,
					image: i.image || "",
					stock: 999,
					in_stock: true,
				};
				const idx = state.products.findIndex(function (p) {
					return p.id === id;
				});
				if (idx >= 0) Object.assign(state.products[idx], mapped);
				else state.products.push(mapped);
			});
		} catch (e) {
			state.cart = state.cart || [];
		}
	}

	async function loadCatalogProducts(filters) {
		const query = filters || {};
		const result = await ShopAPI.getProducts(query);
		shopState.catalogItems = result.items || [];
		shopState.catalogCount = result.items_count || 0;
		state.products = shopState.catalogItems;
		return result;
	}

	async function ensureProductInState(itemCode) {
		let prod = state.products.find(function (p) {
			return p.id === itemCode;
		});
		if (!prod) {
			prod = await ShopAPI.getProductDetail(itemCode);
			const idx = state.products.findIndex(function (p) {
				return p.id === itemCode;
			});
			if (idx >= 0) state.products[idx] = prod;
			else state.products.push(prod);
		}
		return prod;
	}

	// --- Patch initializeState ---
	const _origInitState = initializeState;
	initializeState = function () {
		if (localStorage.getItem("cnc_theme")) {
			state.theme = localStorage.getItem("cnc_theme");
			if (state.theme === "dark") document.body.classList.add("dark-theme");
		}
		if (localStorage.getItem("cnc_lang_v2")) state.lang = localStorage.getItem("cnc_lang_v2");
		else state.lang = "ar";
		applyLanguage(state.lang);
		if (localStorage.getItem("cnc_catalog_view_mode"))
			state.catalogViewMode = localStorage.getItem("cnc_catalog_view_mode");
		else state.catalogViewMode = "grid";
		state.products = [];
		state.cart = [];
		state.orders = [];
		state.slides = [];
	};

	// --- Patch cart operations ---
	window.addToCart = async function (productId) {
		try {
			const prod = await ensureProductInState(productId);
			if (!prod || (prod.stock <= 0 && !prod.in_stock && !prod.on_backorder)) return;
			const existing = state.cart.find(function (i) {
				return i.productId === productId;
			});
			const newQty = existing ? existing.qty + 1 : 1;
			await ShopAPI.updateCart(productId, newQty);
			await syncCartFromServer();
			updateCartBadgeCount();
			renderCartDrawerBody();
			showToast(
				existing ? prod.name + " quantity increased." : t("toast_added_cart"),
				"success"
			);
		} catch (e) {
			showApiError(e);
		}
	};

	window.addDetailToCart = async function (productId) {
		try {
			const prod = await ensureProductInState(productId);
			const qtyInput = document.getElementById("detail-qty-input");
			const qtyToAdd = qtyInput ? parseInt(qtyInput.value, 10) : 1;
			const existing = state.cart.find(function (i) {
				return i.productId === productId;
			});
			const newQty = (existing ? existing.qty : 0) + qtyToAdd;
			await ShopAPI.updateCart(productId, newQty);
			await syncCartFromServer();
			updateCartBadgeCount();
			showToast("Successfully added " + qtyToAdd + " unit(s) of " + prod.name + ".", "success");
			ShopNav.go(ShopNav.cart());
		} catch (e) {
			showApiError(e);
		}
	};

	window.updateCartItemQty = async function (productId, delta) {
		try {
			const item = state.cart.find(function (i) {
				return i.productId === productId;
			});
			if (!item) return;
			const newVal = item.qty + delta;
			if (newVal <= 0) {
				await removeCartItem(productId);
				return;
			}
			await ShopAPI.updateCart(productId, newVal);
			await syncCartFromServer();
			updateCartBadgeCount();
			renderCartView();
		} catch (e) {
			showApiError(e);
		}
	};

	window.removeCartItem = async function (productId, isDrawer) {
		try {
			await ShopAPI.updateCart(productId, 0);
			await syncCartFromServer();
			updateCartBadgeCount();
			if (isDrawer) renderCartDrawerBody();
			else renderCartView();
			showToast(t("toast_removed_cart"), "info");
		} catch (e) {
			showApiError(e);
		}
	};

	// --- Patch renderCatalogView to load from API ---
	const _origRenderCatalog = renderCatalogView;
	renderCatalogView = async function (activeCategory, activeBrand) {
		try {
			const search = document.getElementById("catalog-search")?.value || "";
			const inStock = document.getElementById("filter-instock")?.checked;
			const maxPrice = document.getElementById("filter-price-range")?.value;
			const fieldFilters = {};
			if (activeCategory && activeCategory !== "all") {
				fieldFilters.item_group = CATEGORIES[activeCategory] || activeCategory;
			}
			if (activeBrand) fieldFilters.brand = activeBrand;
			await loadCatalogProducts({
				search: search || undefined,
				field_filters: fieldFilters,
				start: 0,
			});
			if (inStock) {
				state.products = state.products.filter(function (p) {
					return p.in_stock || p.stock > 0;
				});
			}
			if (maxPrice) {
				state.products = state.products.filter(function (p) {
					return p.price <= parseFloat(maxPrice);
				});
			}
		} catch (e) {
			console.error(e);
		}
		_origRenderCatalog(activeCategory, activeBrand);
	};

	// --- Patch renderDetailView ---
	const _origRenderDetail = renderDetailView;
	renderDetailView = async function (productId) {
		if (!productId) return;
		try {
			const prod = await ShopAPI.getProductDetail(productId);
			const idx = state.products.findIndex(function (p) {
				return p.id === productId;
			});
			if (idx >= 0) state.products[idx] = prod;
			else state.products.push(prod);
		} catch (e) {
			console.error(e);
		}
		_origRenderDetail(productId);
	};

	// --- Patch renderCartView ---
	const _origRenderCart = renderCartView;
	renderCartView = async function () {
		await syncCartFromServer();
		_origRenderCart();
		if (state._cartTotals) {
			const c = state._cartTotals;
			const subEl = document.getElementById("cart-subtotal");
			const shipEl = document.getElementById("cart-shipping");
			const totalEl = document.getElementById("cart-grandtotal");
			if (subEl) subEl.innerText = formatMoney(c.subtotal, c.currency);
			if (shipEl)
				shipEl.innerText =
					c.shipping > 0 ? formatMoney(c.shipping, c.currency) : "FREE FREIGHT";
			if (totalEl) totalEl.innerText = formatMoney(c.grand_total, c.currency);
		}
		loadShippingControls();
	};

	async function loadShippingControls() {
		try {
			const [govs, rules] = await Promise.all([
				ShopAPI.getGovernorates(),
				ShopAPI.getShippingRules(),
			]);
			shopState.governorates = govs || [];
			shopState.shippingRules = rules || [];
			const govSelect = document.getElementById("cart-shipping-destination");
			const ruleSelect = document.getElementById("cart-shipping-rule");
			if (govSelect) {
				govSelect.innerHTML = '<option value="">Select Governorate *</option>';
				shopState.governorates.forEach(function (g) {
					govSelect.innerHTML +=
						'<option value="' + g.name + '">' + g.governorate_name + "</option>";
				});
			}
			if (ruleSelect) {
				ruleSelect.innerHTML = '<option value="">Select Shipping Company *</option>';
				(rules || []).forEach(function (r) {
					ruleSelect.innerHTML += '<option value="' + r[0] + '">' + r[1] + "</option>";
				});
			}
			await loadSavedAddresses();
		} catch (e) {
			console.error(e);
		}
	}

	async function loadSavedAddresses() {
		const group = document.getElementById("saved-address-group");
		const select = document.getElementById("saved-address-select");
		if (!select) return;

		if (shopState.is_guest || window.SHOP_BOOT?.is_guest) {
			if (group) group.style.display = "none";
			return;
		}

		try {
			const data = await ShopAPI.getCustomerAddresses();
			const addresses = data?.addresses || [];
			const contact = data?.primary_contact || null;
			shopState.savedAddresses = addresses;
			shopState.checkoutContactName = contact?.name || "";
			shopState.checkoutAddressName = "";

			select.innerHTML = '<option value="">Enter new address</option>';
			addresses.forEach(function (addr) {
				const label =
					(addr.address_title || addr.address_line1 || addr.name) +
					(addr.city ? ", " + addr.city : "");
				select.innerHTML +=
					'<option value="' + addr.name + '">' + label + "</option>";
			});

			if (group) {
				group.style.display = addresses.length ? "block" : "none";
			}

			select.onchange = function () {
				applySavedAddress(select.value);
			};

			if (contact?.first_name) {
				const nameEl = document.getElementById("cust-name");
				if (nameEl && !nameEl.value) nameEl.value = contact.first_name;
			}
			if (contact?.mobile_no) {
				const phoneEl = document.getElementById("cust-phone");
				if (phoneEl && !phoneEl.value) phoneEl.value = contact.mobile_no;
			}
		} catch (e) {
			if (group) group.style.display = "none";
		}
	}

	function applySavedAddress(addressName) {
		if (!addressName) {
			shopState.checkoutAddressName = "";
			return;
		}
		const addr = (shopState.savedAddresses || []).find(function (a) {
			return a.name === addressName;
		});
		if (!addr) return;

		shopState.checkoutAddressName = addr.name;
		const addressEl = document.getElementById("cust-address");
		if (addressEl) {
			addressEl.value = [addr.address_line1, addr.city, addr.country]
				.filter(Boolean)
				.join(", ");
		}
	}

	// --- Patch checkout form ---
	const _origInitCheckout = initCheckoutForm;
	initCheckoutForm = function () {
		const form = document.getElementById("checkout-delivery-form");
		if (!form) return;
		form.addEventListener("submit", async function (e) {
			e.preventDefault();
			if (shopState.booted && (window.SHOP_BOOT?.is_guest || shopState.is_guest)) {
				showToast("Please log in to checkout.", "info");
				ShopNav.go(ShopNav.login(window.location.pathname + window.location.search));
				return;
			}
			if (!state.cart.length) return;

			const btn = form.querySelector('button[type="submit"]');
			if (btn) {
				btn.disabled = true;
				btn.textContent = "Processing...";
			}

			try {
				const addressLine = document.getElementById("cust-address").value.trim();
				const parts = addressLine.split(",").map(function (s) {
					return s.trim();
				});
				const addressData = {
					address_line1: parts[0] || addressLine,
					city: parts[1] || parts[0] || "Cairo",
					country: "Egypt",
				};
				const contactData = {
					first_name: document.getElementById("cust-name").value.trim(),
					mobile_no: document.getElementById("cust-phone").value.trim(),
				};

				let addressName;
				if (shopState.checkoutAddressName && shopState.checkoutContactName) {
					addressName = await ShopAPI.updateCustomerInfo(
						shopState.checkoutAddressName,
						shopState.checkoutContactName,
						addressData,
						contactData
					);
				} else {
					addressName = await ShopAPI.addCustomerInfo(addressData, contactData);
				}
				await ShopAPI.updateCartAddress(addressName);

				const shippingRule = document.getElementById("cart-shipping-rule")?.value;
				const governorate = document.getElementById("cart-shipping-destination")?.value;
				if (!shippingRule || !governorate) {
					showToast("Please select shipping company and governorate.", "info");
					return;
				}
				await ShopAPI.updateCartShipping(shippingRule, governorate);

				const orderId = await ShopAPI.placeOrder();
				shopState.currentPaymentOrder = { order_id: orderId };
				state.cart = [];
				updateCartBadgeCount();
				ShopNav.go(ShopNav.payment(orderId));
			} catch (err) {
				showApiError(err);
			} finally {
				if (btn) {
					btn.disabled = false;
					btn.textContent = t("cart_proceed");
				}
			}
		});
	};

	// --- Patch payment view ---
	const _origRenderPayment = renderPaymentView;
	renderPaymentView = async function () {
		const orderId =
			window.SHOP_BOOT?.order_id ||
			new URLSearchParams(window.location.search).get("order_id") ||
			shopState.currentPaymentOrder?.order_id;

		if (!orderId) {
			showToast("No order found. Please complete checkout first.", "info");
			ShopNav.go(ShopNav.cart());
			return;
		}

		try {
			const order = await ShopAPI.getOrderForPayment(orderId);
			shopState.currentPaymentOrder = order;
			document.getElementById("payment-amount").innerText =
				order.grand_total_formatted || formatMoney(order.grand_total, order.currency);
			document.getElementById("payment-ref-text").innerText =
				"Order Reference ID: #" + order.order_id;
			const submitBtn = document.getElementById("submit-payment-btn");
			if (submitBtn) {
				submitBtn.onclick = function () {
					submitPaymentProof(order);
				};
			}
			window.selectPaymentMethod("instapay");
			resetUploadZone();
			injectPaymentNumbers();
		} catch (e) {
			showApiError(e);
			ShopNav.go(ShopNav.cart());
		}
	};

	function injectPaymentNumbers() {
		const opts = window.SHOP_BOOT?.payment_options || shopState.paymentOptions || [];
		const methods = {
			instapay: opts.find(function (o) {
				return o.key === "instapay";
			}),
			vodafone: opts.find(function (o) {
				return o.key === "vodafone_cash";
			}),
			etisalat: opts.find(function (o) {
				return o.key === "etisalat_cash";
			}),
		};
		if (methods.instapay && methods.instapay.number) {
			PAYMENT_METHODS.instapay.value = methods.instapay.number;
		}
		if (methods.vodafone && methods.vodafone.number) {
			PAYMENT_METHODS.vodafone.value = methods.vodafone.number;
		}
		if (methods.etisalat && methods.etisalat.number) {
			PAYMENT_METHODS.etisalat.value = methods.etisalat.number;
		}
	}

	window.selectPaymentMethod = function (methodKey) {
		const map = { instapay: "instapay", vodafone: "vodafone_cash", etisalat: "etisalat_cash" };
		state.selectedPaymentMethod = map[methodKey] || methodKey;
		const cards = document.querySelectorAll(".payment-method-card");
		cards.forEach(function (card) {
			card.classList.toggle("active", card.dataset.method === methodKey);
		});
		const method = PAYMENT_METHODS[methodKey];
		const detailsBox = document.getElementById("payment-details-box");
		if (!method || !detailsBox) return;
		detailsBox.innerHTML =
			'<div class="method-details-wrapper animate-fade-in"><div class="method-details-header"><span class="details-title">' +
			method.name +
			' Details</span><span class="details-note">' +
			method.note +
			'</span></div><div class="details-row"><div class="details-item"><span class="details-lbl">Account Recipient</span><span class="details-val">' +
			method.recipient +
			'</span></div><div class="details-item"><span class="details-lbl">' +
			method.label +
			'</span><span class="details-val">' +
			method.value +
			"</span></div></div></div>";
	};

	// --- Patch submitPaymentProof ---
	window.submitPaymentProof = async function (orderData) {
		if (!state.pendingReceiptFile) return;
		const order = shopState.currentPaymentOrder;
		if (!order || !order.order_id) {
			showToast("No order to submit payment for.", "info");
			return;
		}
		if (!state.selectedPaymentMethod) {
			showToast("Please select a payment method.", "info");
			return;
		}

		const file = state.pendingReceiptFile;
		const reader = new FileReader();
		reader.onload = async function (ev) {
			try {
				const base64 = ev.target.result.split(",")[1];
				await ShopAPI.confirmPayment(
					order.order_id,
					state.selectedPaymentMethod,
					file.name,
					base64
				);
				state.pendingReceiptFile = null;
				showToast("Payment proof submitted successfully!", "success");
				setTimeout(function () {
					ShopNav.go(ShopNav.orders());
				}, 1000);
			} catch (e) {
				showApiError(e);
			}
		};
		reader.readAsDataURL(file);
	};

	// --- Patch orders view ---
	const _origRenderOrders = renderOrdersView;
	renderOrdersView = async function () {
		if (window.SHOP_BOOT?.is_guest || shopState.is_guest) {
			showToast("Please log in to view orders.", "info");
			ShopNav.go(ShopNav.login("/shop/orders"));
			return;
		}
		try {
			state.orders = await ShopAPI.getOrders();
		} catch (e) {
			state.orders = [];
			showApiError(e);
		}
		_origRenderOrders();
	};

	// --- Patch admin views ---
	const _origAdminAnalytics = renderAdminAnalytics;
	renderAdminAnalytics = async function () {
		try {
			const data = await ShopAPI.admin.getAnalytics();
			document.getElementById("admin-revenue-text").innerText =
				formatMoney(data.total_revenue);
			document.getElementById("admin-orders-text").innerText =
				data.order_count + " Synced";
			document.getElementById("admin-conversion-text").innerText =
				data.conversion_percent + "%";
			const chartContainer = document.getElementById("sales-chart-container");
			if (chartContainer && data.chart_points) {
				const points = data.chart_points.length ? data.chart_points : [0];
				const maxVal = Math.max.apply(null, points.concat([1])) * 1.1;
				const svgWidth = chartContainer.offsetWidth || 500;
				const svgHeight = 240;
				const padding = 30;
				const xStep = (svgWidth - padding * 2) / Math.max(points.length - 1, 1);
				let polylineCoords = "";
				points.forEach(function (val, index) {
					const x = padding + index * xStep;
					const y = svgHeight - padding - (val / maxVal) * (svgHeight - padding * 2);
					polylineCoords += x + "," + y + " ";
				});
				chartContainer.innerHTML =
					'<svg width="100%" height="100%" viewBox="0 0 ' +
					svgWidth +
					" " +
					svgHeight +
					'"><polyline fill="none" stroke="var(--primary-blue)" stroke-width="3" points="' +
					polylineCoords +
					'"/></svg>';
			}
		} catch (e) {
			showApiError(e);
		}
	};

	const _origAdminInventory = renderAdminInventory;
	renderAdminInventory = async function () {
		try {
			state.products = await ShopAPI.admin.getInventory();
		} catch (e) {
			showApiError(e);
		}
		_origAdminInventory();
	};

	const _origAdminOrders = renderAdminOrdersApproval;
	renderAdminOrdersApproval = async function () {
		const tableBody = document.getElementById("admin-receipt-rows");
		if (!tableBody) return;
		try {
			const pending = await ShopAPI.admin.getPendingOrders();
			tableBody.innerHTML = "";
			if (!pending.length) {
				tableBody.innerHTML =
					'<tr><td colspan="6" style="text-align:center;padding:48px;color:var(--text-muted);">No draft orders awaiting payment.</td></tr>';
				return;
			}
			pending.forEach(function (order) {
				const tr = document.createElement("tr");
				tr.innerHTML =
					"<td><code>" +
					order.id +
					"</code></td><td>" +
					order.customer +
					"</td><td>" +
					formatMoney(order.grandTotal, order.currency) +
					'</td><td><span class="badge-sync">Awaiting Payment</span></td><td>' +
					order.date +
					'</td><td><button class="btn btn-primary btn-sm" onclick="window.approveAdminOrder(\'' +
					order.id +
					"')\">Approve & Submit</button></td>";
				tableBody.appendChild(tr);
			});
		} catch (e) {
			showApiError(e);
		}
	};

	window.approveAdminOrder = async function (orderId) {
		try {
			await ShopAPI.admin.approveOrder(orderId);
			showToast("Order submitted.", "success");
			renderAdminOrdersApproval();
		} catch (e) {
			showApiError(e);
		}
	};

	const _origAdminSlides = renderAdminSlideshowTable;
	renderAdminSlideshowTable = async function () {
		try {
			state.slides = await ShopAPI.admin.getSlides();
		} catch (e) {
			console.error(e);
		}
		_origAdminSlides();
	};

	window.syncErpProducts = async function () {
		try {
			await loadCatalogProducts({ start: 0 });
			showToast("Product catalog refreshed from ERPNext.", "success");
			if (state.activeAdminTab === "inventory") renderAdminInventory();
		} catch (e) {
			showApiError(e);
		}
	};

	// --- Patch home view ---
	const _origRenderHome = renderHomeView;
	renderHomeView = async function () {
		try {
			const homeData = await ShopAPI.getHomeData();
			if (homeData.products?.length) state.products = homeData.products;
			if (homeData.slides?.length) state.slides = homeData.slides;
			if (homeData.categories) Object.assign(CATEGORIES, homeData.categories);
		} catch (e) {
			console.error(e);
		}
		_origRenderHome();
	};

	// --- Admin slide customizer ---
	initSlideCustomizerForm = function () {
		const form = document.getElementById("admin-add-slide-form");
		const dropZone = document.getElementById("slide-upload-zone");
		const fileInput = document.getElementById("slide-file-input");
		const removeBtn = document.getElementById("remove-slide-img-btn");

		if (!form) return;

		if (dropZone && fileInput) {
			dropZone.addEventListener("click", () => {
				if (!pendingSlideImageFile) fileInput.click();
			});
			dropZone.addEventListener("dragover", (e) => {
				e.preventDefault();
				dropZone.classList.add("hover");
			});
			dropZone.addEventListener("dragleave", () => dropZone.classList.remove("hover"));
			dropZone.addEventListener("drop", (e) => {
				e.preventDefault();
				dropZone.classList.remove("hover");
				if (e.dataTransfer.files.length > 0) handleSlideFile(e.dataTransfer.files[0]);
			});
			fileInput.addEventListener("change", (e) => {
				if (e.target.files.length > 0) handleSlideFile(e.target.files[0]);
			});
		}

		if (removeBtn) {
			removeBtn.addEventListener("click", (e) => {
				e.stopPropagation();
				resetSlideUploadZone();
			});
		}

		form.addEventListener("submit", async function (e) {
			e.preventDefault();
			const eyebrow = document.getElementById("slide-eyebrow").value;
			const title = document.getElementById("slide-title").value;
			const subtitle = document.getElementById("slide-subtitle").value;
			const link = document.getElementById("slide-link").value || "/shop/catalog";
			const imgSelect = document.getElementById("slide-image-select").value;
			let imageSrc = imgSelect;

			if (imgSelect === "custom") {
				if (!pendingSlideImageFile) {
					showToast("Please upload a custom slide image first.", "info");
					return;
				}
				const previewImg = document.getElementById("slide-preview-img");
				imageSrc = previewImg ? previewImg.src : "";
			}

			try {
				await ShopAPI.admin.saveSlide({
					eyebrow: eyebrow.toUpperCase(),
					title: title,
					subtitle: subtitle,
					link: link,
					image: imageSrc,
				});
				state.slides = await ShopAPI.admin.getSlides();
				showToast("Slide saved to Webshop Settings.", "success");
				form.reset();
				resetSlideUploadZone();
				const uploadGroup = document.getElementById("slide-custom-upload-group");
				if (uploadGroup) uploadGroup.style.display = "none";
				renderAdminSlideshowTable();
				renderHeroSlides();
			} catch (err) {
				showApiError(err);
			}
		});
	};

	const _origDeleteSlide = window.deleteSlide;
	window.deleteSlide = async function (index) {
		const slide = state.slides[index];
		if (!slide) return;
		try {
			if (slide.id) {
				state.slides = await ShopAPI.admin.deleteSlide(slide.id);
			} else {
				state.slides.splice(index, 1);
			}
			renderAdminSlideshowTable();
			renderHeroSlides();
			showToast("Slide removed.", "info");
		} catch (e) {
			showApiError(e);
		}
	};

	// --- Auth forms ---
	function initAuthForms() {
		const loginForm = document.getElementById("login-form");
		if (loginForm) {
			loginForm.onsubmit = async function (e) {
				e.preventDefault();
				try {
					await ShopAPI.login(
						document.getElementById("login-email").value.trim(),
						document.getElementById("login-password").value
					);
					const redirect = window.SHOP_BOOT?.redirect_to || "/shop";
					window.location.href = redirect;
				} catch (err) {
					showToast("Invalid email or password.", "info");
				}
			};
		}

		const signupForm = document.getElementById("signup-form");
		if (signupForm) {
			signupForm.onsubmit = async function (e) {
				e.preventDefault();
				const pwd = document.getElementById("signup-password").value;
				const confirm = document.getElementById("signup-confirm-password").value;
				if (pwd !== confirm) {
					showToast("Passwords do not match.", "info");
					return;
				}
				try {
					const result = await ShopAPI.signUp(
						document.getElementById("signup-email").value.trim(),
						document.getElementById("signup-name").value.trim(),
						pwd,
						document.getElementById("signup-phone").value.trim()
					);
					if (result && result[0] === 1) {
						showToast("Account created! Please log in.", "success");
						ShopNav.go(ShopNav.login());
					} else {
						showToast(result[1] || "Signup failed.", "info");
					}
				} catch (err) {
					showApiError(err);
				}
			};
		}
	}

	// --- Hook DOMContentLoaded ---
	document.addEventListener("DOMContentLoaded", function () {
		bootstrapShop().then(function () {
			initAuthForms();
			const syncBtn = document.getElementById("sync-erpnext-btn");
			if (syncBtn) {
				syncBtn.onclick = function (e) {
					e.preventDefault();
					window.syncErpProducts();
				};
			}
		});
	});
})();
