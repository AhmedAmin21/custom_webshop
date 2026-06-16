frappe.ready(function () {
    console.log("[custom_webshop] custom_signup.js loaded");

    function bind_checkbox_toggle() {
        var $cb = $("#has_past_transactions");
        if (!$cb.length) {
            console.warn("[custom_webshop] #has_past_transactions not found");
            return;
        }
        $cb.off("change.cw").on("change.cw", function () {
            if ($(this).is(":checked")) {
                $("#mobile_field_group").css("display", "block");
                $("#signup_mobile").prop("required", true);
            } else {
                $("#mobile_field_group").css("display", "none");
                $("#signup_mobile").prop("required", false).val("");
            }
        });
        console.log("[custom_webshop] checkbox toggle bound");
    }

    function bind_custom_signup_handler() {
        console.log("[custom_webshop] binding custom signup handler");

        // Unbind Frappe's default signup handler so we can replace it
        $(".form-signup").off("submit");

        $(".form-signup").on("submit", function (event) {
            event.preventDefault();
            console.log("[custom_webshop] custom signup submit triggered");

            var email = $("#signup_email").val().trim();
            var full_name = frappe.utils.xss_sanitise(($("#signup_fullname").val() || "").trim());
            var pwd = $("#signup_password").val();
            var confirm_pwd = $("#signup_confirm_password").val();
            var redirect_to = frappe.utils.sanitise_redirect(frappe.utils.get_url_arg("redirect-to"));
            var has_past_transactions = $("#has_past_transactions").is(":checked") ? 1 : 0;
            var mobile = $("#signup_mobile").val().trim().replace(/\s|-/g, "");

            console.log("[custom_webshop] signup args:", {
                email: email,
                full_name: full_name,
                has_past_transactions: has_past_transactions,
                mobile: mobile
            });

            if (!email || !validate_email(email) || !full_name) {
                login.set_status(__("Valid email and name required"), 'red');
                return false;
            }

            if (!pwd || !confirm_pwd) {
                login.set_status(__("Please enter both password fields"), 'red');
                return false;
            }

            if (pwd !== confirm_pwd) {
                login.set_status(__("Passwords do not match"), 'red');
                return false;
            }

            if (has_past_transactions && !mobile) {
                login.set_status(__("Please enter your mobile number"), 'red');
                return false;
            }

            // Check password strength if policy is enabled
            frappe.call({
                method: "frappe.core.doctype.user.user.test_password_strength",
                args: { new_password: pwd },
                callback: function (r) {
                    var feedback = r.message && r.message.feedback;
                    if (feedback && !feedback.password_policy_validation_passed) {
                        var msg = feedback.warning || feedback.suggestions[0] || __("Password is too weak");
                        login.set_status(msg, 'red');
                        return false;
                    }
                    submit_signup(email, full_name, pwd, redirect_to, has_past_transactions, mobile);
                },
                error: function () {
                    // Policy might be disabled; just submit
                    submit_signup(email, full_name, pwd, redirect_to, has_past_transactions, mobile);
                }
            });

            return false;
        });
    }

    // Bind immediately (login page may already be rendered)
    bind_checkbox_toggle();
    bind_custom_signup_handler();

    // Also re-bind when login_rendered fires (for hashchange navigation)
    $(document).on('login_rendered', function () {
        console.log("[custom_webshop] login_rendered event received");
        bind_checkbox_toggle();
        bind_custom_signup_handler();
    });

    function submit_signup(email, full_name, pwd, redirect_to, has_past_transactions, mobile) {
        var args = {
            cmd: "frappe.core.doctype.user.user.sign_up",
            email: email,
            full_name: full_name,
            pwd: pwd,
            redirect_to: redirect_to,
            has_past_transactions: has_past_transactions,
            mobile: mobile
        };

        console.log("[custom_webshop] calling sign_up API");
        login.call(args).then(function (r) {
            console.log("[custom_webshop] sign_up response:", r);
            if (r.message && cint(r.message[0]) === 1) {
                var msg = r.message[1];
                if (msg && msg.status === "match_found") {
                    show_match_confirmation(msg, email);
                } else {
                    login.set_status(__("Success"), 'green');
                    frappe.msgprint(msg.message || msg);
                    setTimeout(function () {
                        window.location.href = "/login";
                    }, 2000);
                }
            } else {
                login.set_status((r.message && r.message[1]) || __("Error"), 'red');
            }
        }).catch(function (err) {
            console.error("[custom_webshop] sign_up error:", err);
            login.set_status(__("Signup failed. Please try again."), 'red');
        });
    }

    function show_match_confirmation(data, user_email) {
        var invoice = data.invoice;
        var items_text = "";
        if (invoice && invoice.items && invoice.items.length) {
            items_text = invoice.items.map(function (it) {
                return it.item_name + " (x" + cint(it.qty) + ")";
            }).join(", ");
        }

        var message = __(
            "We found a customer record for <b>{0}</b> with a recent invoice <b>{1}</b> on <b>{2}</b> for <b>{3}</b> containing: <b>{4}</b>.<br><br>Is this you?",
            [
                data.customer_name,
                invoice ? invoice.name : "",
                invoice ? frappe.format_date(invoice.posting_date) : "",
                invoice ? format_currency(invoice.grand_total) : "",
                items_text
            ]
        );

        var d = new frappe.ui.Dialog({
            title: __("Confirm Your Account"),
            fields: [
                {
                    fieldtype: "HTML",
                    fieldname: "message",
                    options: "<div class='text-muted'>" + message + "</div>"
                }
            ],
            primary_action_label: __("Yes, that's me"),
            primary_action: function () {
                d.hide();
                confirm_mapping(data.customer, data.contact, user_email);
            },
            secondary_action_label: __("No, create new account"),
            secondary_action: function () {
                d.hide();
                login.set_status(__("Account created successfully! Please log in."), 'green');
                setTimeout(function () {
                    window.location.href = "/login";
                }, 2000);
            }
        });
        d.show();
    }

    function confirm_mapping(customer, contact, user_email) {
        frappe.call({
            method: "custom_webshop.api.auth.confirm_customer_mapping",
            args: {
                customer: customer,
                contact: contact,
                user: user_email
            },
            callback: function (r) {
                if (r.message && r.message.status === "mapped") {
                    login.set_status(__("Account linked successfully! Please log in."), 'green');
                } else {
                    login.set_status(__("Account created successfully! Please log in."), 'green');
                }
                setTimeout(function () {
                    window.location.href = "/login";
                }, 2000);
            },
            error: function () {
                login.set_status(__("Account created successfully! Please log in."), 'green');
                setTimeout(function () {
                    window.location.href = "/login";
                }, 2000);
            }
        });
    }

    function format_currency(value) {
        if (typeof value === "number") {
            return value.toFixed(2);
        }
        return value;
    }
});
