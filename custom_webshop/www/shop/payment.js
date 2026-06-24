(function () {
	"use strict";

	var shopBase = (window.cnc_shop_routes && window.cnc_shop_routes.base) || "/shop";
	var selected_option = null;

	function show_error(message) {
		$("#payment-error").html(message).show();
		$("#payment-success").hide();
	}

	function show_success(message) {
		$("#payment-success").html(message).show();
		$("#payment-error").hide();
	}

	function show_loading(show) {
		$("#submit-payment").prop("disabled", show).text(show ? __("Submitting...") : __("Submit Payment Confirmation"));
	}

	function bind_payment_options() {
		$(".payment-option").on("click", function () {
			$(".payment-option").removeClass("border-primary selected");
			$(this).addClass("border-primary selected");
			selected_option = $(this).data("option");
		});
		var first = $(".payment-option").first();
		if (first.length) {
			first.addClass("border-primary selected");
			selected_option = first.data("option");
		}
	}

	function submit_payment() {
		var order_id = $("#order-id").val();
		var ordersBase = $("#shop-orders-base").val() || shopBase + "/orders";
		var file_input = $("#payment-proof")[0];

		if (!selected_option) return show_error(__("Please select a payment method."));
		if (!file_input.files || !file_input.files[0]) return show_error(__("Please upload a payment confirmation document."));

		var file = file_input.files[0];
		if (file.size > 5 * 1024 * 1024) return show_error(__("File size must be less than 5MB."));

		var reader = new FileReader();
		reader.onload = function (e) {
			show_loading(true);
			frappe.call({
				method: "custom_webshop.api.payment.confirm_payment",
				args: {
					order_id: order_id,
					payment_method: selected_option,
					filename: file.name,
					file_content: e.target.result.split(",")[1],
				},
				callback: function (r) {
					show_loading(false);
					if (r.exc) {
						show_error(__("Something went wrong. Please try again."));
					} else if (r.message && r.message.success) {
						show_success(__("Payment confirmation submitted successfully. Redirecting..."));
						setTimeout(function () {
							window.location.href = ordersBase + "/" + encodeURIComponent(order_id);
						}, 2000);
					} else {
						show_error((r.message && r.message.error) || __("Something went wrong."));
					}
				},
			});
		};
		reader.readAsDataURL(file);
	}

	frappe.ready(function () {
		bind_payment_options();
		$("#payment-form").on("submit", function (e) {
			e.preventDefault();
			submit_payment();
		});
	});
})();
