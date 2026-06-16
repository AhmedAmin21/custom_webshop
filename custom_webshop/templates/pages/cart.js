// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// JS exclusive to /cart page — custom_webshop override
// Changes:
// 1. "Request for Quote" button text → "Place Order"
// 2. Creates a Sales Order instead of a Quotation
// 3. Friendly address prompt if no address selected
// 4. Redirects to /orders/ instead of /quotations/
// 5. Debounced qty updates (1000ms) with subtle freeze
// 6. Strong "Please wait" freeze for Place Order

frappe.provide("webshop.webshop.shopping_cart");
var shopping_cart = webshop.webshop.shopping_cart;

$.extend(shopping_cart, {
	show_error: function(title, text) {
		$("#cart-container").html('<div class="msg-box"><h4>' +
			title + '</h4><p class="text-muted">' + text + '</p></div>');
	},

	_debounceTimers: {},

	debouncedCartUpdate: function(item_code, qty, additional_notes) {
		if (this._debounceTimers[item_code]) {
			clearTimeout(this._debounceTimers[item_code]);
		}
		$(`.cart-qty[data-item-code="${item_code}"]`).addClass('cart-qty-updating');

		this._debounceTimers[item_code] = setTimeout(() => {
			$(`.cart-qty[data-item-code="${item_code}"]`).removeClass('cart-qty-updating');
			shopping_cart.shopping_cart_update({
				item_code: item_code,
				qty: qty,
				additional_notes: additional_notes
			});
			delete this._debounceTimers[item_code];
		}, 1000);
	},

	bind_events: function() {
		shopping_cart.bind_place_order();
		shopping_cart.bind_request_quotation();
		shopping_cart.bind_change_qty();
		shopping_cart.bind_remove_cart_item();
		shopping_cart.bind_change_notes();
		shopping_cart.bind_coupon_code();
	},

	bind_place_order: function() {
		$(".btn-place-order").on("click", function() {
			shopping_cart.place_order(this);
		});
	},

	bind_request_quotation: function() {
		$('.btn-request-for-quotation').on('click', function() {
			shopping_cart.request_quotation(this);
		});
	},

	bind_change_qty: function() {
		$(".cart-items").on("change", ".cart-qty", function() {
			var item_code = $(this).attr("data-item-code");
			var newVal = $(this).val();
			shopping_cart.debouncedCartUpdate(item_code, newVal);
		});

		$(".cart-items").on('click', '.number-spinner button', function () {
			var btn = $(this),
				input = btn.closest('.number-spinner').find('input'),
				oldValue = input.val().trim(),
				newVal = 0;

			if (btn.attr('data-dir') == 'up') {
				newVal = parseInt(oldValue) + 1;
			} else {
				if (oldValue > 1) {
					newVal = parseInt(oldValue) - 1;
				}
			}
			input.val(newVal);

			let notes = input.closest("td").siblings().find(".notes").text().trim();
			var item_code = input.attr("data-item-code");
			shopping_cart.debouncedCartUpdate(item_code, newVal, notes);
		});
	},

	bind_change_notes: function() {
		$('.cart-items').on('change', 'textarea', function() {
			const $textarea = $(this);
			const item_code = $textarea.attr('data-item-code');
			const qty = $textarea.closest('tr').find('.cart-qty').val();
			const notes = $textarea.val();
			shopping_cart.debouncedCartUpdate(item_code, qty, notes);
		});
	},

	bind_remove_cart_item: function() {
		$(".cart-items").on("click", ".remove-cart-item", (e) => {
			const $remove_cart_item_btn = $(e.currentTarget);
			var item_code = $remove_cart_item_btn.data("item-code");

			shopping_cart.shopping_cart_update({
				item_code: item_code,
				qty: 0
			});
		});
	},

	render_tax_row: function($cart_taxes, doc, shipping_rules) {
		var shipping_selector;
		if(shipping_rules) {
			shipping_selector = '<select class="form-control">' + $.map(shipping_rules, function(rule) {
				return '<option value="' + rule[0] + '">' + rule[1] + '</option>' }).join("\n") +
				'</select>';
		}

		var $tax_row = $(repl('<div class="row">\
			<div class="col-md-9 col-sm-9">\
				<div class="row">\
					<div class="col-md-9 col-md-offset-3">' +
					(shipping_selector || '<p>%(description)s</p>') +
					'</div>\
				</div>\
			</div>\
			<div class="col-md-3 col-sm-3 text-right">\
				<p' + (shipping_selector ? ' style="margin-top: 5px;"' : "") + '>%(formatted_tax_amount)s</p>\
			</div>\
		</div>', doc)).appendTo($cart_taxes);

		if(shipping_selector) {
			$tax_row.find('select option').each(function(i, opt) {
				if($(opt).html() == doc.description) {
					$(opt).attr("selected", "selected");
				}
			});
			$tax_row.find('select').on("change", function() {
				shopping_cart.apply_shipping_rule($(this).val(), this);
			});
		}
	},

	apply_shipping_rule: function(rule, btn) {
		return frappe.call({
			btn: btn,
			type: "POST",
			method: "webshop.webshop.shopping_cart.cart.apply_shipping_rule",
			args: { shipping_rule: rule },
			callback: function(r) {
				if(!r.exc) {
					shopping_cart.render(r.message);
				}
			}
		});
	},

	freeze: function(mode) {
		if (window.location.pathname !== "/cart") return;

		if (mode === 'strong') {
			$('.cart-container').addClass('cart-freeze-strong');
		} else {
			$('.cart-container').addClass('cart-freeze-subtle');
		}
	},

	unfreeze: function(mode) {
		if (window.location.pathname !== "/cart") return;

		if (mode === 'strong') {
			$('.cart-container').removeClass('cart-freeze-strong');
		} else {
			$('.cart-container').removeClass('cart-freeze-subtle');
		}
	},

	place_order: function(btn) {
		$(btn).prop('disabled', true).text(__('Please wait...'));
		shopping_cart.freeze('strong');

		return frappe.call({
			type: "POST",
			method: "webshop.webshop.shopping_cart.cart.place_order",
			btn: btn,
			callback: function(r) {
				shopping_cart.unfreeze('strong');
				$(btn).prop('disabled', false).text(__('Place Order'));

				if(r.exc) {
					var msg = "";
					if(r._server_messages) {
						msg = JSON.parse(r._server_messages || []).join("<br>");
					}

					$("#cart-error")
						.empty()
						.html(msg || frappe._("Something went wrong!"))
						.toggle(true);
				} else {
					$(btn).hide();
					window.location.href = '/orders/' + encodeURIComponent(r.message);
				}
			}
		});
	},

	request_quotation: function(btn) {
		const shippingAddress = $('[data-section="shipping-address"]')
			.find('[data-address-name][data-active]').attr('data-address-name');
		const billingAddress = $('[data-section="billing-address"]')
			.find('[data-address-name][data-active]').attr('data-address-name');

		if (!shippingAddress && !billingAddress) {
			const d = new frappe.ui.Dialog({
				title: __('Customer Information Required'),
				fields: [
					{
						fieldtype: 'HTML',
						fieldname: 'message',
						options: `<p>${__("Please add your customer information before placing your order.")}</p>`
					}
				],
				primary_action_label: __('Add Customer Information'),
				primary_action: () => {
					d.hide();
					shopping_cart.open_customer_info_dialog('add');
				},
				secondary_action_label: __('Cancel'),
				secondary_action: () => {
					d.hide();
				}
			});
			d.show();
			return;
		}

		$(btn).prop('disabled', true).text(__('Please wait...'));
		shopping_cart.freeze('strong');

		return frappe.call({
			type: "POST",
			method: "webshop.webshop.shopping_cart.cart.request_for_quotation",
			btn: btn,
			callback: function(r) {
				shopping_cart.unfreeze('strong');
				$(btn).prop('disabled', false).text(__('Place Order'));

				if(r.exc) {
					var msg = "";
					if(r._server_messages) {
						msg = JSON.parse(r._server_messages || []).join("<br>");
					}

					$("#cart-error")
						.empty()
						.html(msg || frappe._("Something went wrong!"))
						.toggle(true);
				} else {
					$(btn).hide();
					window.location.href = '/orders/' + encodeURIComponent(r.message);
				}
			}
		});
	},

	bind_coupon_code: function() {
		$(".bt-coupon").on("click", function() {
			shopping_cart.apply_coupon_code(this);
		});
	},

	apply_coupon_code: function(btn) {
		return frappe.call({
			type: "POST",
			method: "webshop.webshop.shopping_cart.cart.apply_coupon_code",
			btn: btn,
			args : {
				applied_code : $('.txtcoupon').val(),
				applied_referral_sales_partner: $('.txtreferral_sales_partner').val()
			},
			callback: function(r) {
				if (r && r.message){
					location.reload();
				}
			}
		});
	},

	open_customer_info_dialog: function(mode = 'add', existingData = {}) {
		const user_fullname = $('#user-fullname').val() || frappe.session.user_fullname || '';
		const isEdit = mode === 'edit';

		const d = new frappe.ui.Dialog({
			title: isEdit ? __('Edit Customer Information') : __('Customer Information'),
			fields: [
				{
					fieldtype: 'Section Break',
					label: __('Contact Information')
				},
				{
					label: __('Full Name'),
					fieldname: 'first_name',
					fieldtype: 'Data',
					reqd: 1,
					read_only: 1,
					default: existingData.first_name || user_fullname
				},
				{
					label: __('Mobile / Phone'),
					fieldname: 'mobile_no',
					fieldtype: 'Data',
					reqd: 1,
					default: existingData.mobile_no || ''
				},
				{
					fieldtype: 'Section Break',
					label: __('Shipping Address')
				},
				{
					label: __('Address'),
					fieldname: 'address_line1',
					fieldtype: 'Data',
					reqd: 1,
					default: existingData.address_line1 || ''
				},
				{
					label: __('City / Town'),
					fieldname: 'city',
					fieldtype: 'Data',
					reqd: 1,
					default: existingData.city || ''
				},
				{
					label: __('Country'),
					fieldname: 'country',
					fieldtype: 'Link',
					options: 'Country',
					only_select: true,
					reqd: 1,
					default: existingData.country || ''
				}
			],
			primary_action_label: isEdit ? __('Update') : __('Save'),
			primary_action: (values) => {
				const address_data = {
					address_line1: values.address_line1,
					city: values.city,
					country: values.country
				};
				const contact_data = {
					first_name: values.first_name,
					mobile_no: values.mobile_no
				};

				let method, args;
				if (isEdit && existingData.address_name) {
					method = 'custom_webshop.shopping_cart.cart_override.update_customer_info';
					args = {
						address_name: existingData.address_name,
						address_data: JSON.stringify(address_data),
						contact_name: existingData.contact_name,
						contact_data: JSON.stringify(contact_data)
					};
				} else {
					method = 'custom_webshop.shopping_cart.cart_override.add_customer_info';
					args = {
						address_data: JSON.stringify(address_data),
						contact_data: JSON.stringify(contact_data)
					};
				}

				frappe.call({
					method: method,
					args: args,
					freeze: true,
					freeze_message: __('Saving...'),
					callback: function(r) {
						if (r.message) {
							d.hide();
							// Link the new address to cart
							frappe.call({
								method: 'webshop.webshop.shopping_cart.cart.update_cart_address',
								args: {
									address_type: 'Shipping',
									address_name: r.message
								},
								callback: function() {
									window.location.reload();
								}
							});
						}
					}
				});
			},
			secondary_action_label: __('Cancel'),
			secondary_action: () => {
				d.hide();
			}
		});

		d.show();
	},

	bind_address_events: function() {
		// Open dialog for new customer info
		$(document).on('click', '.btn-customer-info', () => {
			shopping_cart.open_customer_info_dialog('add');
		});

		// Open dialog for editing existing
		$(document).on('click', '.btn-edit-address', (e) => {
			const $container = $(e.currentTarget).closest('.address-container');
			const $card = $container.find('.address-card');
			const addressName = $container.attr('data-address-name');
			const contactName = $card.attr('data-contact-name');

			// Fetch existing data from the card
			const firstName = $card.find('.customer-name').text().trim();
			const mobileNo = $card.find('.phone-value').text().trim();
			const addressLine1 = $card.find('.customer-address-line').text().trim();
			const locationText = $card.find('.customer-location').text().trim();
			const city = locationText.split(',')[0]?.trim() || '';
			const country = locationText.split(',')[1]?.trim() || '';

			shopping_cart.open_customer_info_dialog('edit', {
				address_name: addressName,
				contact_name: contactName,
				first_name: firstName,
				mobile_no: mobileNo,
				address_line1: addressLine1,
				city: city,
				country: country
			});
		});
	}
});

frappe.ready(function() {
	if (window.location.pathname === "/cart") {
		$(".cart-icon").hide();
	}
	shopping_cart.parent = $(".cart-container");
	shopping_cart.bind_events();
	shopping_cart.bind_address_events();

	$('.btn-request-for-quotation').text('Place Order');
});

function show_terms() {
	var html = $(".cart-terms").html();
	frappe.msgprint(html);
}
