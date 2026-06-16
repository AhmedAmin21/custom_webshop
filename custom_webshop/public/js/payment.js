frappe.provide("custom_webshop.payment");

$(document).ready(function() {
	custom_webshop.payment.init();
});

custom_webshop.payment = {
	selected_option: null,

	init: function() {
		this.bind_payment_options();
		this.bind_form_submit();
	},

	bind_payment_options: function() {
		const self = this;
		$(".payment-option").on("click", function() {
			$(".payment-option").removeClass("border-primary selected");
			$(this).addClass("border-primary selected");
			self.selected_option = $(this).data("option");
		});

		// Select first option by default if available
		const first_option = $(".payment-option").first();
		if (first_option.length) {
			first_option.addClass("border-primary selected");
			self.selected_option = first_option.data("option");
		}
	},

	bind_form_submit: function() {
		const self = this;
		$("#payment-form").on("submit", function(e) {
			e.preventDefault();
			self.submit_payment();
		});
	},

	submit_payment: function() {
		const self = this;
		const order_id = $("#order-id").val();
		const file_input = $("#payment-proof")[0];

		if (!self.selected_option) {
			self.show_error(__("Please select a payment method."));
			return;
		}

		if (!file_input.files || !file_input.files[0]) {
			self.show_error(__("Please upload a payment confirmation document."));
			return;
		}

		const file = file_input.files[0];

		// Validate file size (max 5MB)
		if (file.size > 5 * 1024 * 1024) {
			self.show_error(__("File size must be less than 5MB."));
			return;
		}

		const reader = new FileReader();
		reader.onload = function(e) {
			const base64_content = e.target.result.split(",")[1];

			self.show_loading(true);
			self.hide_messages();

			frappe.call({
				type: "POST",
				method: "custom_webshop.api.payment.confirm_payment",
				args: {
					order_id: order_id,
					payment_method: self.selected_option,
					filename: file.name,
					file_content: base64_content
				},
				callback: function(r) {
					self.show_loading(false);

					if (r.exc) {
						let msg = "";
						if (r._server_messages) {
							msg = JSON.parse(r._server_messages || []).join("<br>");
						}
						self.show_error(msg || __("Something went wrong. Please try again."));
					} else if (r.message && r.message.success) {
						self.show_success(__("Payment confirmation submitted successfully. Redirecting..."));
						setTimeout(function() {
							window.location.href = "/orders/" + encodeURIComponent(order_id);
						}, 2000);
					} else {
						self.show_error((r.message && r.message.error) || __("Something went wrong. Please try again."));
					}
				},
				error: function() {
					self.show_loading(false);
					self.show_error(__("Something went wrong. Please try again."));
				}
			});
		};

		reader.onerror = function() {
			self.show_error(__("Failed to read the file. Please try again."));
		};

		reader.readAsDataURL(file);
	},

	show_loading: function(show) {
		const btn = $("#submit-payment");
		if (show) {
			btn.prop("disabled", true).text(__("Submitting..."));
		} else {
			btn.prop("disabled", false).text(__("Submit Payment Confirmation"));
		}
	},

	show_error: function(message) {
		$("#payment-error").html(message).show();
		$("#payment-success").hide();
	},

	show_success: function(message) {
		$("#payment-success").html(message).show();
		$("#payment-error").hide();
	},

	hide_messages: function() {
		$("#payment-error, #payment-success").hide();
	}
};
