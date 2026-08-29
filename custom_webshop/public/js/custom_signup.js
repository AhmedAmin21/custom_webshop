frappe.ready(function () {
    // If the custom login page controller (page-login.js) is active, let it handle signup
    if (window.LOGIN_CONTEXT) {
        return;
    }
    console.log("[custom_webshop] custom_signup.js loaded");

    function bind_custom_signup_handler() {
        console.log("[custom_webshop] binding custom signup handler");

        // Unbind Frappe's default signup handler so we can replace it
        $(".form-signup").off("submit");

        $(".form-signup").on("submit", function (event) {
            event.preventDefault();
            console.log("[custom_webshop] custom signup submit triggered");

            var email = $("#signup_email").val().trim();
            var full_name = frappe.utils.xss_sanitise(($("#signup_fullname").val() || "").trim());
            var mobile = $("#signup_mobile").val().trim();
            var pwd = $("#signup_password").val();
            var confirm_pwd = $("#signup_confirm_password").val();
            var redirect_to = frappe.utils.sanitise_redirect(frappe.utils.get_url_arg("redirect-to"));

            console.log("[custom_webshop] signup args:", {
                email: email,
                full_name: full_name,
                mobile: mobile
            });

            if (!email || !validate_email(email) || !full_name) {
                login.set_status(__("Valid email and name required"), 'red');
                return false;
            }

            if (!mobile) {
                login.set_status(__("Please enter your mobile number"), 'red');
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
                    submit_signup(email, full_name, pwd, redirect_to, mobile);
                },
                error: function () {
                    // Policy might be disabled; just submit
                    submit_signup(email, full_name, pwd, redirect_to, mobile);
                }
            });

            return false;
        });
    }

    // Bind immediately (login page may already be rendered)
    bind_custom_signup_handler();

    // Also re-bind when login_rendered fires (for hashchange navigation)
    $(document).on('login_rendered', function () {
        console.log("[custom_webshop] login_rendered event received");
        bind_custom_signup_handler();
    });

    function submit_signup(email, full_name, pwd, redirect_to, mobile) {
        var args = {
            cmd: "frappe.core.doctype.user.user.sign_up",
            email: email,
            full_name: full_name,
            pwd: pwd,
            mobile_no: mobile,
            redirect_to: redirect_to
        };

        console.log("[custom_webshop] calling sign_up API");
        login.call(args).then(function (r) {
            console.log("[custom_webshop] sign_up response:", r);
            if (r.message && cint(r.message[0]) === 1) {
                var msg = r.message[1];
                login.set_status(__("Success"), 'green');
                frappe.msgprint(msg.message || msg);
                setTimeout(function () {
                    window.location.href = "/login";
                }, 2000);
            } else {
                login.set_status((r.message && r.message[1]) || __("Error"), 'red');
            }
        }).catch(function (err) {
            console.error("[custom_webshop] sign_up error:", err);
            login.set_status(__("Signup failed. Please try again."), 'red');
        });
    }
});
