frappe.provide("frappe.listview_settings");

(function () {
	const existing_onload =
		frappe.listview_settings["Item"] &&
		frappe.listview_settings["Item"].onload;

	frappe.listview_settings["Item"] = frappe.listview_settings["Item"] || {};

	frappe.listview_settings["Item"].onload = function (listview) {
		if (existing_onload) {
			existing_onload(listview);
		}

		listview.page.add_action_item(__("Publish in Website"), function () {
			const checked_items = listview.get_checked_items();
			if (!checked_items || checked_items.length === 0) {
				frappe.msgprint({
					message: __("Please select at least one item to publish."),
					indicator: "orange",
					title: __("No Items Selected"),
				});
				return;
			}

			if (checked_items.length > 50) {
				frappe.msgprint({
					message: __(
						"Cannot publish more than 50 items at a time to prevent system load.<br>" +
							"You selected <b>{0}</b> items.<br><br>" +
							"Please select 50 or fewer items.",
						[checked_items.length]
					),
					indicator: "red",
					title: __("Batch Limit Exceeded (Max 50)"),
				});
				return;
			}

			const item_codes = checked_items.map(function (item) {
				return item.name || item;
			});

			frappe.confirm(
				__(
					"Are you sure you want to publish <b>{0}</b> item(s) to the website?",
					[item_codes.length]
				),
				function () {
					frappe.call({
						method: "custom_webshop.api.items.publish_items_to_website",
						args: {
							item_codes: item_codes,
						},
						freeze: true,
						freeze_message: __(
							"Publishing {0} item(s) to website...",
							[item_codes.length]
						),
						callback: function (r) {
							if (r.message) {
								const res = r.message;
								const indicator =
									res.failed > 0
										? "orange"
										: res.skipped > 0
										? "blue"
										: "green";

								let message_html = `<div style="font-size: 13px; margin-bottom: 12px;">
									<b>${__("Publishing Summary")}</b><br>
									• ${__("Published")}: <b style="color: #2e7d32;">${res.published}</b><br>
									• ${__("Skipped")}: <b style="color: #ed6c02;">${res.skipped}</b><br>
									• ${__("Failed")}: <b style="color: #d32f2f;">${res.failed}</b><br>
									• ${__("Time Taken")}: <b>${res.time_taken}s</b>
								</div>`;

								if (res.details && res.details.length > 0) {
									message_html += `<div style="margin-top: 15px;">
										<h6 style="margin-bottom: 8px;"><b>${__("Items Not Published & Reasons:")}</b></h6>
										<div style="max-height: 240px; overflow-y: auto; border: 1px solid #d1d8dd; border-radius: 4px;">
											<table class="table table-bordered table-condensed" style="margin-bottom: 0; font-size: 12px;">
												<thead>
													<tr style="background-color: #f7fafc;">
														<th style="width: 35%;">${__("Item Code")}</th>
														<th style="width: 20%;">${__("Status")}</th>
														<th style="width: 45%;">${__("Reason")}</th>
													</tr>
												</thead>
												<tbody>
													${res.details
														.map(function (d) {
															const badge_class =
																d.status === "Failed"
																	? "red"
																	: "orange";
															return `<tr>
																<td><b>${frappe.utils.escape_html(d.item_code)}</b></td>
																<td><span class="indicator ${badge_class}">${frappe.utils.escape_html(d.status)}</span></td>
																<td>${frappe.utils.escape_html(d.reason)}</td>
															</tr>`;
														})
														.join("")}
												</tbody>
											</table>
										</div>
									</div>`;
								}

								frappe.msgprint({
									message: message_html,
									indicator: indicator,
									title: __("Website Publishing Complete"),
								});

								listview.refresh();
							}
						},
					});
				}
			);
		});
	};
})();
