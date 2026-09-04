/* ==========================================================================
   CNCLeaders — Shared Store
   Handles: state, i18n, theme, API adapter, cart badge, toast, session
   ========================================================================== */

const TRANSLATIONS = {
    en: {
        nav_home: "Home", nav_catalog: "All Products", nav_orders: "Track Orders", nav_admin: "Admin Panel",
        home_shop_material: "Shop by Material", home_shop_material_sub: "Browse components by manufacturing material",
        material_wood: "Wood & MDF", material_acrylic: "Marble & Glass", material_metal: "Aluminum & Metals",
        material_all: "View all categories", home_shop_category: "Shop by Category",
        home_shop_category_sub: "Swipe through certified high-precision parts by class",
        home_shop_attribute: "Shop by Attribute", home_shop_attribute_sub: "Browse products grouped by their attributes",
        filter_attribute: "Attribute",
        home_shop_tool_family: "Shop by Tool Family", home_shop_tool_family_sub: "Browse products by cutting tool family",
        filter_tool_family: "Tool Family", filter_material: "Material",
        home_trending: "Trending Equipment", home_trending_sub: "Most demanded components",
        home_shop_brand: "Shop by Certified Brand", home_shop_brand_sub: "Genuine components from authorized industrial manufacturers",
        filter_search: "Search", filter_search_placeholder: "Search by model or spec...",
        filter_category: "Category", filter_stock: "Stock Status", filter_instock_only: "In Stock Only",
        filter_max_price: "Max Price", filter_brand: "Brand", btn_reset_filters: "Reset Filters",
        catalog_sort: "Sort: ", sort_default: "Default Sync Order", sort_price_asc: "Price: Low to High",
        sort_price_desc: "Price: High to Low", sort_alpha: "A-Z Name", cart_selected: "Your Selected Hardware",
        cart_cost_structure: "Order Cost Structure", cart_subtotal: "Subtotal", cart_total_weight: "Total Weight",
        cart_shipping: "Shipping", cart_shipping_company: "Shipping Company",
        cart_total: "Grand Total", cart_delivery: "Delivery & Shipping Address", cart_name: "Full Name / Company Name *",
        cart_name_placeholder: "e.g. John Doe, Machining LLC", cart_phone: "Contact Phone Number *",
        cart_phone_placeholder: "e.g. +1 555-0199", cart_address: "Shipping Address *",
        cart_address_placeholder: "Street address, unit, city, state, zip code...", cart_notes: "Machining Details / Delivery Instructions",
        cart_notes_placeholder: "Notes (e.g. loading dock hours, fork-lift requirements)", cart_proceed: "Proceed to checkout",
        drawer_proceed: "Proceed to Full Form",
        cart_empty: "Your cart is empty.", cart_goto_shop: "Browse Products",
        payment_title: "Checkout", payment_subtitle: "To complete order processing and trigger ERPNext packaging, please wire the total amount and upload your receipt screenshot below.",
        payment_amount_label: "Amount Outstanding", payment_method: "Choose Payment Method",
        payment_upload_title: "Provide Payment Confirmation", payment_upload_text: "Drag and drop your bank slip screenshot or click to browse files",
        payment_upload_note: "Accepted formats: JPG, PNG (Max 5MB)", payment_submit: "Submit Payment Proof",
        payment_track: "Back to Orders", orders_title: "Purchase Orders",
        orders_subtitle: "", btn_add_to_cart: "Add to Cart",
        btn_out_of_stock: "Out of Stock", btn_remove: "Remove", btn_details: "View Details",
        toast_cart_restored: "We put your basket back.",
        toast_added_cart: "Added to Cart!", toast_removed_cart: "Component removed from cart.",
        catalog_results: "Showing {count} components", catalog_no_results: "No components match your filters.",
        orders_empty: "No orders found.", order_status_draft: "Awaiting Payment", order_pay_now: "Pay Now",
        order_view: "View Order", order_date: "Date", order_total: "Total", order_status: "Status",
        auth_login_title: "Log in", auth_login_sub: "",
        auth_email: "E-mail Address", auth_password: "Password", auth_login_btn: "Authenticate",
        auth_login_btn_loading: "Signing in...",
        auth_no_account: "No account?", auth_signup_link: "Create one",
        auth_signup_title: "New Account", auth_signup_sub: "Register for industrial product procurement.",
        auth_name: "Full Name / Company", auth_phone: "Mobile Number", auth_confirm_password: "Confirm Password",
        auth_signup_btn: "Create Account",
        auth_signup_btn_loading: "Creating Account...",
        auth_has_account: "Already have an account?", auth_login_link: "Sign In",
        auth_forgot_link: "Forgot password?",
        auth_forgot_title: "Reset password",
        auth_forgot_sub: "Enter your email and we'll send you a reset link.",
        auth_back_to_login: "Back to sign in",
        auth_forgot_btn: "Send reset link",
        auth_forgot_btn_loading: "Sending...",
        // ── Verified signup wizard ──────────────────────────────────
        su_step: "Step {n} of {total}",
        su_type_title: "Create your account", su_type_sub: "Who is this account for?",
        su_type_individual: "Personal",
        su_type_company: "Company",
        su_details_title: "Your details", su_details_sub: "We'll verify your email and mobile number next.",
        su_full_name: "Full name (3 parts)", su_full_name_ph: "Your full name",
        su_company_name: "Company name", su_company_name_ph: "Acme Trading",
        su_contact_person: "Contact person (3 parts)",
        su_email: "E-mail address", su_email_ph: "you@example.com",
        su_phone: "Mobile number", su_phone_ph: "10 01234567",
        su_continue: "Continue", su_back: "Back", su_sending: "Sending...",
        su_email_otp_title: "Check your email", su_email_otp_sub: "We sent a {n}-digit code to {target}.",
        su_phone_otp_title: "Check your phone", su_phone_otp_sub: "We sent a {n}-digit code to {target}.",
        su_code: "Verification code", su_verify: "Verify", su_verifying: "Verifying...",
        su_resend: "Resend code", su_resend_in: "Resend in {n}s", su_sends_left: "{n} resends left",
        su_change_email: "Change email", su_change_phone: "Change number",
        su_change_email_title: "Change email address", su_change_phone_title: "Change mobile number",
        su_save_and_send: "Save and send code",
        su_match_title: "Is this you?",
        su_match_sub: "We found an existing customer record that may be yours. Only you can tell us.",
        su_match_company: "Company",
        su_match_company_note: "This number is registered to a business. If you work there, this is the right record — your account will be linked to it.",
        su_match_yes: "Yes, this is me", su_match_no: "No, this isn't me",
        su_back_to_record: "Back to that record",
        su_match_name: "Name", su_match_phone: "Phone", su_match_address: "Address",
        su_match_governorate: "Governorate", su_match_country: "Country",
        su_match_hidden: "Some details are hidden until you confirm this is your record.",
        su_blocked_email: "{email} is already registered here.",
        su_blocked_phone: "{phone} is already registered here.",
        su_blocked_customer: "The customer record these details belong to already has an account.",
        su_own_title: "You already have an account",
        su_own_sub: "This email and phone both belong to an account here. If it's yours, we'll sign you straight in.",
        su_own_yes: "Yes, these are my data",
        su_own_no: "This is not my data",
        su_name_title: "Which name should we use?",
        su_name_sub: "Your account can use either. Your customer record keeps its own until our team reviews it.",
        su_name_keep_label: "Current recorded name",
        su_name_keep_hint: "Keep the name on your record",
        su_name_use_label: "Newly entered name",
        su_name_use_hint: "Use the name I just entered",
        su_name_note: "Either way you'll be signed in to the same account.",
        su_recover_title: "Set a new password",
        su_recover_sub: "You'll use this to sign in to your account from now on.",
        su_disputed_title: "Set a new password",
        su_disputed_sub: "You'll be signed in to that account. We'll ask our team to check the details on it.",
        su_password_title: "Choose a password", su_password_sub: "Last step — your details are verified.",
        su_password: "Password", su_confirm_password: "Confirm password",
        su_finish: "Create account", su_finishing: "Creating account...",
        su_done_title: "You're all set", su_done_sub: "Taking you to the shop...",
        su_blocked_title: "You already have an account",
        su_blocked_sub: "Sign in with your existing account, or reset your password if you've forgotten it.",
        su_blocked_restart: "Sign up with different details",
        su_goto_login: "Sign in", su_goto_forgot: "Reset password",
        su_expired_title: "This signup expired", su_expired_sub: "It's been a while — please start again.",
        su_restart: "Start again",
        su_err_name: "We need 3 parts of your name — your first name, your father's name and your family name.",
        su_err_company: "Please enter your company name.",
        su_err_email: "Please enter a valid email address.",
        su_err_phone: "Please enter a valid mobile number, for example {example}.",
        su_phone_len: "Numbers in {country} have {need} digits \u2014 you have typed {have}.",
        su_err_code: "Please enter the code we sent you.",
        su_pw_title: "A good password:",
        su_pw_length: "8 characters or more",
        su_pw_mix: "has letters and numbers",
        su_pw_personal: "is not your name, email or phone",
        su_pw_common: "is not a common word like \"password\"",
        su_err_password: "Please enter and confirm your password.",
        su_err_password_weak: "That password is easy to guess. Please follow the four points above.",
        su_err_password_match: "The two passwords do not match.",
        su_err_generic: "Something went wrong. Please try again.",
        su_name_adjusted: "We saved your name as \"{name}\" — our records use a standard spelling.",
        su_country_search: "Search countries...",
        su_country_none: "No country matches that.",
        loading: "Loading...", error_generic: "Something went wrong. Please try again.",
        shipping_destination: "Shipping Destination (Governorate)", shipping_select: "Select governorate...",
        shipping_company_select: "Select shipping company...",
        cart_shipping_required: "Please select a shipping company and governorate.",
        cart_delivery_required: "Please fill in your name, phone, and shipping address.",
        stock_in: "In Stock",
        stock_out: "Out of Stock",
        stock_low: "Low Stock: Only {qty} left",
        stock_backorder: "Available on backorder",
        nav_search_placeholder: "Search cutting tools, part codes, specs...",
        home_hero_browse: "Browse All Products",
        home_hero_catalog: "Catalog",
        home_hero_contact: "Contact Us",
        certified_partner: "Certified Partner",
        price_on_request: "Price on Request",
        view_more: "View More",
        filter_all: "All",
        filter_all_brands: "All Brands",
        filter_clear_all: "Clear All",
        filter_view_more: "View More",
        filter_view_less: "View Less",
        filter_mobile_btn: "Filter Products",
        filter_mobile_title: "Filters",
        filter_active: "Active Filters:",
        btn_apply_filters: "Show Results"
    },
    ar: {
        nav_home: "الرئيسية", nav_catalog: "جميع المنتجات", nav_orders: "تتبع الطلبات", nav_admin: "لوحة التحكم",
        home_shop_material: "تسوق حسب خامة التشغيل", home_shop_material_sub: "تصفح المكونات حسب مادة التصنيع",
        material_wood: "الأخشاب و ال MDF", material_acrylic: "الرخام والزجاج", material_metal: "الألومنيوم والمعادن",
        material_all: "عرض كل التصنيفات", home_shop_category: "تسوق حسب الفئة",
        home_shop_category_sub: "تصفح أجزاء عالية الدقة معتمدة حسب الفئة",
        home_shop_attribute: "تسوق حسب الخصائص", home_shop_attribute_sub: "تصفح المنتجات مجمعةً حسب خصائصها",
        filter_attribute: "الخصائص",
        home_shop_tool_family: "تسوق حسب عائلة الأداة", home_shop_tool_family_sub: "تصفح المنتجات حسب عائلة أداة القطع",
        filter_tool_family: "عائلة الأداة", filter_material: "الخامة",
        home_trending: "المعدات الشائعة",
        home_trending_sub: "المكونات الأكثر طلباً لورش ومصانع الـ CNC", home_shop_brand: "تسوق حسب العلامة التجارية المعتمدة",
        home_shop_brand_sub: "مكونات وأدوات أصلية من الشركات المصنعة المعتمدة", filter_search: "بحث",
        filter_search_placeholder: "ابحث بالنموذج أو المواصفات...", filter_category: "الفئة", filter_stock: "حالة المخزون",
        filter_instock_only: "متوفر فقط", filter_max_price: "الحد الأقصى للسعر", filter_brand: "العلامة التجارية",
        btn_reset_filters: "إعادة ضبط المرشحات", catalog_sort: "ترتيب: ", sort_default: "الترتيب الافتراضي",
        sort_price_asc: "السعر: من الأقل للأعلى", sort_price_desc: "السعر: من الأعلى للأقل", sort_alpha: "أ-ي حسب الاسم",
        cart_selected: "أجهزتك المختارة", cart_cost_structure: "هيكل تكلفة الطلب", cart_subtotal: "المجموع الفرعي",
        cart_total_weight: "الوزن الإجمالي", cart_shipping: "الشحن", cart_shipping_company: "شركة الشحن",
        cart_total: "الإجمالي النهائي", cart_delivery: "عنوان التوصيل والشحن",
        cart_name: "الاسم الكامل / اسم الشركة *", cart_name_placeholder: "مثال: جون دو، شركة الآلات المحدودة",
        cart_phone: "رقم هاتف الاتصال *", cart_phone_placeholder: "مثال: +1 555-0199", cart_address: "عنوان الشحن *",
        cart_address_placeholder: "عنوان الشارع، الوحدة، المدينة، الولاية، الرمز البريدي...", cart_notes: "تفاصيل الآلات / تعليمات التوصيل",
        cart_notes_placeholder: "ملاحظات (مثل ساعات الرصيف، متطلبات الرافعة الشوكية)", cart_proceed: "متابعة لإتمام الشراء",
        drawer_proceed: "متابعة إلى النموذج الكامل",
        cart_empty: "سلتك فارغة.", cart_goto_shop: "تصفح المنتجات",
        payment_title: "الدفع", payment_subtitle: "لإكمال معالجة الطلب وبدء التغليف، يرجى تحويل المبلغ الإجمالي وتحميل لقطة شاشة للإيصال أدناه.",
        payment_amount_label: "المبلغ المستحق", payment_method: "اختر طريقة الدفع", payment_upload_title: "تقديم تأكيد الدفع",
        payment_upload_text: "قم بسحب وإفلات لقطة شاشة لإيصال البنك أو انقر لاستعراض الملفات", payment_upload_note: "الصيغ المقبولة: JPG، PNG (الحد الأقصى 5 ميجابايت)",
        payment_submit: "إرسال إثبات الدفع", payment_track: "العودة للطلبات", orders_title: "طلبات الشراء",
        orders_subtitle: "", btn_add_to_cart: "أضف إلى السلة",
        btn_out_of_stock: "نفذت الكمية", btn_remove: "إزالة", btn_details: "عرض التفاصيل",
        toast_cart_restored: "أعدنا سلتك كما تركتها.",
        toast_added_cart: "تمت الإضافة إلى السلة!", toast_removed_cart: "تم إزالة المكون من السلة.",
        catalog_results: "عرض {count} مكونات", catalog_no_results: "لا توجد مكونات تطابق معاييرك.",
        orders_empty: "لا توجد طلبات.", order_status_draft: "في انتظار الدفع", order_pay_now: "ادفع الآن",
        order_view: "عرض الطلب", order_date: "التاريخ", order_total: "الإجمالي", order_status: "الحالة",
        auth_login_title: "تسجيل الدخول", auth_login_sub: "",
        auth_email: "البريد الإلكتروني", auth_password: "كلمة المرور", auth_login_btn: "تسجيل الدخول",
        auth_login_btn_loading: "جاري تسجيل الدخول...",
        auth_no_account: "ليس لديك حساب؟", auth_signup_link: "إنشاء حساب",
        auth_signup_title: "حساب جديد", auth_signup_sub: "سجل لشراء المنتجات الصناعية.",
        auth_name: "الاسم الكامل / الشركة", auth_phone: "رقم الموبايل", auth_confirm_password: "تأكيد كلمة المرور",
        auth_signup_btn: "إنشاء حساب",
        auth_signup_btn_loading: "جاري إنشاء الحساب...",
        auth_has_account: "هل لديك حساب بالفعل؟", auth_login_link: "تسجيل الدخول",
        auth_forgot_link: "نسيت كلمة المرور؟",
        auth_forgot_title: "إعادة تعيين كلمة المرور",
        auth_forgot_sub: "اكتب بريدك الإلكتروني وسنرسل لك رابط إعادة التعيين.",
        auth_back_to_login: "العوده لتسجيل الدخول",
        auth_forgot_btn: "إرسال رابط إعادة التعيين",
        auth_forgot_btn_loading: "جاري الإرسال...",
        // ── معالج إنشاء الحساب الموثق ────────────────────────────────
        su_step: "خطوة {n} من {total}",
        su_type_title: "إنشاء حسابك", su_type_sub: "هذا الحساب لمن؟",
        su_type_individual: "فرد",
        su_type_company: "شركة",
        su_details_title: "بياناتك", su_details_sub: "سوف نتحقق من بريدك الإلكتروني ورقم موبايلك بعد ذلك.",
        su_full_name: "الاسم الثلاثي", su_full_name_ph: "اسمك الثلاثي",
        su_company_name: "اسم الشركة", su_company_name_ph: "شركة النخبه",
        su_contact_person: "الشخص المسؤول (الاسم الثلاثي)",
        su_email: "البريد الإلكتروني", su_email_ph: "you@example.com",
        su_phone: "رقم الموبايل", su_phone_ph: "10 01234567",
        su_continue: "متابعة", su_back: "رجوع", su_sending: "جاري الإرسال...",
        su_email_otp_title: "تفقد بريدك الإلكتروني", su_email_otp_sub: "أرسلنا رمزا من {n} أرقام إلى {target}.",
        su_phone_otp_title: "تفقد هاتفك", su_phone_otp_sub: "أرسلنا رمزا من {n} أرقام إلى {target}.",
        su_code: "رمز التحقق", su_verify: "تحقق", su_verifying: "جاري التحقق...",
        su_resend: "إعادة إرسال الرمز", su_resend_in: "إعادة الإرسال خلال {n} ثانية",
        su_sends_left: "متبقي {n} محاولات إرسال",
        su_change_email: "تغيير البريد الإلكتروني", su_change_phone: "تغيير الرقم",
        su_change_email_title: "تغيير البريد الإلكتروني", su_change_phone_title: "تغيير رقم الموبايل",
        su_save_and_send: "حفظ وإرسال الرمز",
        su_match_title: "هل هذا انت؟",
        su_match_sub: "وجدنا سجل عميل قد يكون خاصا بك. انت وحدك من يستطيع تأكيد ذلك.",
        su_match_company: "الشركة",
        su_match_company_note: "هذا الرقم مسجل باسم شركة. إذا كنت تعمل بها فهذا هو السجل الصحيح، وسيتم ربط حسابك به.",
        su_match_yes: "نعم، هذا انا", su_match_no: "لا، ليس انا",
        su_back_to_record: "الرجوع إلى ذلك السجل",
        su_match_name: "الاسم", su_match_phone: "الهاتف", su_match_address: "العنوان",
        su_match_governorate: "المحافظة", su_match_country: "الدولة",
        su_match_hidden: "بعض التفاصيل مخفية حتى تؤكد أن هذا سجلك.",
        su_blocked_email: "{email} مسجل لدينا بالفعل.",
        su_blocked_phone: "{phone} مسجل لدينا بالفعل.",
        su_blocked_customer: "سجل العميل الخاص بهذه البيانات له حساب بالفعل.",
        su_own_title: "لديك حساب بالفعل",
        su_own_sub: "هذا البريد وهذا الرقم مسجلان معا في حساب لدينا. إن كان حسابك، سندخلك إليه مباشرة.",
        su_own_yes: "نعم، هذه بياناتي",
        su_own_no: "هذه ليست بياناتي",
        su_name_title: "أي اسم تريد استخدامه؟",
        su_name_sub: "يمكن لحسابك استخدام أي منهما. أما سجل العميل فيحتفظ باسمه حتى يراجعه فريقنا.",
        su_name_keep_label: "الاسم المسجل حاليا",
        su_name_keep_hint: "الاحتفاظ بالاسم المسجل",
        su_name_use_label: "الاسم الذي أدخلته",
        su_name_use_hint: "استخدام الاسم الذي أدخلته",
        su_name_note: "في الحالتين سيتم تسجيل دخولك إلى الحساب نفسه.",
        su_recover_title: "اختر كلمة مرور جديدة",
        su_recover_sub: "ستستخدمها لتسجيل الدخول إلى حسابك من الآن فصاعدا.",
        su_disputed_title: "اختر كلمة مرور جديدة",
        su_disputed_sub: "سندخلك إلى ذلك الحساب، وسنطلب من فريقنا مراجعة البيانات المسجلة عليه.",
        su_password_title: "اختر كلمة المرور", su_password_sub: "الخطوة الأخيرة — تم التحقق من بياناتك.",
        su_password: "كلمة المرور", su_confirm_password: "تأكيد كلمة المرور",
        su_finish: "إنشاء الحساب", su_finishing: "جاري إنشاء الحساب...",
        su_done_title: "تم بنجاح", su_done_sub: "جاري تحويلك إلى المتجر...",
        su_blocked_title: "لديك حساب بالفعل",
        su_blocked_sub: "سجل الدخول بحسابك الحالي، أو أعد تعيين كلمة المرور إذا نسيتها.",
        su_blocked_restart: "التسجيل ببيانات أخرى",
        su_goto_login: "تسجيل الدخول", su_goto_forgot: "إعادة تعيين كلمة المرور",
        su_expired_title: "انتهت صلاحية هذا التسجيل", su_expired_sub: "مر وقت طويل — يرجى البدء من جديد.",
        su_restart: "ابدأ من جديد",
        su_err_name: "نحتاج اسمك ثلاثيا — اسمك واسم والدك واسم العائلة.",
        su_err_company: "يرجى إدخال اسم الشركة.",
        su_err_email: "يرجى إدخال بريد إلكتروني صحيح.",
        su_err_phone: "يرجى إدخال رقم موبايل صحيح، مثال {example}.",
        su_phone_len: "أرقام {country} تتكون من {need} خانة \u2014 أدخلت {have}.",
        su_err_code: "يرجى إدخال الرمز الذي أرسلناه إليك.",
        su_pw_title: "كلمة المرور الجيده:",
        su_pw_length: "٨ خانات أو أكثر",
        su_pw_mix: "تحتوي على حروف وأرقام",
        su_pw_personal: "ليست اسمك أو بريدك أو رقمك",
        su_pw_common: "ليست كلمه شائعه مثل \"password\"",
        su_err_password: "يرجى إدخال كلمة المرور وتأكيدها.",
        su_err_password_weak: "كلمة المرور سهلة التخمين. يرجى اتباع النقاط الأربع بالأعلى.",
        su_err_password_match: "كلمتا المرور غير متطابقتين.",
        su_err_generic: "حدث خطأ ما. يرجى المحاولة مرة أخرى.",
        su_name_adjusted: "تم حفظ اسمك بالصيغه \"{name}\" — سجلاتنا تستخدم صيغه موحده.",
        su_country_search: "ابحث عن دوله...",
        su_country_none: "لا توجد دوله مطابقه.",
        loading: "جاري التحميل...", error_generic: "حدث خطأ. يرجى المحاولة مرة أخرى.",
        shipping_destination: "وجهة الشحن (المحافظة)", shipping_select: "اختر المحافظة...",
        shipping_company_select: "اختر شركة الشحن...",
        cart_shipping_required: "يرجى اختيار شركة الشحن والمحافظة.",
        cart_delivery_required: "يرجى إدخال الاسم والهاتف وعنوان الشحن.",
        stock_in: "متوفر بالمخزن",
        stock_out: "نفذت الكمية",
        stock_low: "متبقي كمية محدودة: فقط {qty}",
        stock_backorder: "متاح للطلب المسبق",
        nav_search_placeholder: "ابحث عن أدوات القطع، الأكواد، المواصفات...",
        home_hero_browse: "تصفح جميع المنتجات",
        home_hero_catalog: "الكاتلوج",
        home_hero_contact: "تواصل معنا",
        certified_partner: "شريك معتمد",
        price_on_request: "السعر عند الطلب",
        view_more: "عرض الكل",
        filter_all: "الكل",
        filter_all_brands: "جميع العلامات التجارية",
        filter_clear_all: "مسح الكل",
        filter_view_more: "عرض المزيد",
        filter_view_less: "عرض أقل",
        filter_mobile_btn: "تصفية المنتجات",
        filter_mobile_title: "الفلاتر",
        filter_active: "الفلاتر المطبقة:",
        btn_apply_filters: "عرض النتائج"
    }
};

/* --------------------------------------------------------------------------
   Material label map — mirrors item_parser.py MATERIAL_LABELS
   -------------------------------------------------------------------------- */
const MATERIAL_LABELS_JS = {
    "C":   { en: "Carbide",                                 ar: "كربيد" },
    "HSS": { en: "HSS",                                     ar: "صلب عالي السرعات" },
    "TCT": { en: "TCT",                                     ar: "عود كربيد ملحوم في جسم صلب" },
    "CW":  { en: "CW",                                      ar: "شفرات كربيد ملحومة فى جسم صلب" },
    "CM":  { en: "CM",                                      ar: "كربيد يستخدم فى المعادن" },
    "M&G": { en: "M&G",                                     ar: "رخام و زجاج" },
};

/* --------------------------------------------------------------------------
   Store — singleton state container
   -------------------------------------------------------------------------- */
const Store = {
    lang: "ar",
    theme: "light",
    user: null,
    isGuest: true,
    csrfToken: "",

    /* ------------------------------------------------------------------
       Translation helper
       ------------------------------------------------------------------ */
    t(key, params = {}) {
        const dict = TRANSLATIONS[this.lang] || TRANSLATIONS["en"];
        let str = dict[key] !== undefined ? dict[key] : key;
        for (const [k, v] of Object.entries(params)) {
            str = str.replace(`{${k}}`, v);
        }
        return str;
    },

    /* ------------------------------------------------------------------
       Material label helper
       ------------------------------------------------------------------ */
    materialLabel(code) {
        const entry = MATERIAL_LABELS_JS[code];
        if (!entry) return code;
        return entry[this.lang] || entry["en"] || code;
    },

    /* ------------------------------------------------------------------
       Language
       ------------------------------------------------------------------ */
    applyLanguage(lang) {
        this.lang = lang;
        localStorage.setItem("cnc_lang_v2", lang);
        document.documentElement.lang = lang;
        document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
        if (lang === "ar") {
            document.body.classList.add("rtl");
        } else {
            document.body.classList.remove("rtl");
        }
        // Update all i18n elements
        document.querySelectorAll("[data-i18n]").forEach(el => {
            el.textContent = this.t(el.getAttribute("data-i18n"));
        });
        document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
            el.setAttribute("placeholder", this.t(el.getAttribute("data-i18n-placeholder")));
        });
        // Update lang button label
        const langBtnText = document.getElementById("lang-btn-text");
        if (langBtnText) langBtnText.textContent = lang === "en" ? "AR" : "EN";
        // Update cart badge
        this.updateCartBadge();
        // Dispatch global event for active page controllers to re-render dynamic content
        window.dispatchEvent(new CustomEvent("cnc_language_changed", { detail: { lang } }));
    },

    /* ------------------------------------------------------------------
       Theme
       ------------------------------------------------------------------ */
    applyTheme(theme) {
        this.theme = theme;
        localStorage.setItem("cnc_theme", theme);
        if (theme === "dark") {
            document.body.classList.add("dark-theme");
        } else {
            document.body.classList.remove("dark-theme");
        }
        const themeBtn = document.getElementById("theme-btn");
        if (themeBtn) {
            const sun = themeBtn.querySelector(".icon-sun");
            const moon = themeBtn.querySelector(".icon-moon");
            if (theme === "dark") {
                if (sun) sun.style.display = "none";
                if (moon) moon.style.display = "block";
            } else {
                if (sun) sun.style.display = "block";
                if (moon) moon.style.display = "none";
            }
        }
    },

    /* ------------------------------------------------------------------
       Debug log — posts to server (browser cannot reach localhost ingest)
       ------------------------------------------------------------------ */
    debugLog(location, message, data = {}, hypothesisId = "", runId = "") {
        fetch("/api/method/custom_webshop.api.debug_log.log_client_event", {
            method: "POST",
            headers: { "Content-Type": "application/json", "Accept": "application/json" },
            body: JSON.stringify({
                location,
                message,
                data: JSON.stringify(data),
                hypothesis_id: hypothesisId,
                run_id: runId,
            }),
        }).catch(() => {});
    },

    productPrice(item) {
        if (!item) return "—";
        if (item.formatted_price) return item.formatted_price;
        const rate = item.price_list_rate != null ? parseFloat(item.price_list_rate) : (item.price != null ? parseFloat(item.price) : null);
        if (rate != null) {
            if (rate <= 0) {
                return this.lang === "ar" ? "السعر عند الطلب" : "Price on Request";
            }
            const numStr = rate.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            return this.lang === "ar" ? `${numStr} ج.م` : `${numStr} EGP`;
        }
        return "—";
    },

    productLink(item) {
        const slug = item.route || item.item_code || item.name || "";
        return `/product?item=${encodeURIComponent(slug)}`;
    },

    /* ------------------------------------------------------------------
       API Adapter — wraps frappe.call via fetch with CSRF
       Usage: Store.call("app.module.method", { arg: val }).then(r => ...)
       ------------------------------------------------------------------ */
    call(method, args = {}) {
        const token = this.csrfToken ||
            (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";

        return fetch(`/api/method/${method}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Frappe-CSRF-Token": token,
                "Accept": "application/json",
            },
            body: JSON.stringify(args),
        })
        .then(res => {
            // #region agent log
            if (method.includes("get_product_filter_data") || method.includes("is_slide_admin") || method.includes("custom_sign_up")) {
                this.debugLog("store.js:call", "api response", { method, status: res.status, ok: res.ok }, "H3");
            }
            // #endregion
            if (!res.ok) {
                return res.json().then(data => {
                    throw new Error(this.extractApiError(data) || `HTTP ${res.status}`);
                });
            }
            return res.json();
        })
        .then(data => {
            if (data.exc) {
                throw new Error(this.extractApiError(data) || data.exc_type || "Server error");
            }
            return data.message !== undefined ? data.message : data;
        });
    },

    extractApiError(data) {
        if (!data) return "";
        if (data._server_messages) {
            try {
                const msgs = JSON.parse(data._server_messages);
                const parsed = msgs.map(m => {
                    try { return JSON.parse(m).message; } catch { return m; }
                }).filter(Boolean);
                if (parsed.length) return parsed.join(" ");
            } catch { /* ignore */ }
        }
        if (data.message && typeof data.message === "string") return data.message;
        return data.exc_type || "";
    },

    /* ------------------------------------------------------------------
       Guest basket

       A visitor can fill a basket without an account; they are asked to
       sign up when they proceed to the full order form, not before. The
       basket therefore cannot live on the server: ERPNext's own
       update_cart resolves a party first, so building one for a guest
       would create a Customer for somebody who has not proved who they
       are - the exact thing custom_webshop.signup exists to prevent.

       So it lives in this browser, holding item codes and quantities and
       nothing else. Names and prices are fetched from a guest-readable
       endpoint when the drawer is opened, so nothing here goes stale and
       nothing about the catalogue is cached. On sign-in it is replayed
       into the real cart and cleared.
       ------------------------------------------------------------------ */
    GUEST_CART_KEY: "cnc_guest_cart",

    guestCart() {
        try {
            const raw = JSON.parse(localStorage.getItem(this.GUEST_CART_KEY));
            return (raw && typeof raw === "object") ? raw : {};
        } catch (e) {
            return {};
        }
    },

    saveGuestCart(cart) {
        try {
            localStorage.setItem(this.GUEST_CART_KEY, JSON.stringify(cart || {}));
        } catch (e) { /* private mode; the basket is a convenience */ }
    },

    clearGuestCart() {
        try {
            localStorage.removeItem(this.GUEST_CART_KEY);
        } catch (e) { /* nothing to clear */ }
    },

    guestCartCount() {
        const cart = this.guestCart();
        return Object.keys(cart).reduce((sum, code) => sum + (parseInt(cart[code], 10) || 0), 0);
    },

    setGuestQty(itemCode, qty) {
        const cart = this.guestCart();
        const wanted = Math.max(0, parseInt(qty, 10) || 0);
        if (wanted) {
            cart[itemCode] = wanted;
        } else {
            delete cart[itemCode];
        }
        this.saveGuestCart(cart);
    },

    /** Add one item, wherever this visitor's basket happens to live.
     *  Always returns a promise, so callers do not have to know which. */
    addToCart(itemCode, qty = 1) {
        if (!itemCode) return Promise.resolve();

        if (this.isGuest) {
            const cart = this.guestCart();
            this.setGuestQty(itemCode, (parseInt(cart[itemCode], 10) || 0) + qty);
            this.updateCartBadge();
            return Promise.resolve();
        }

        return this.call("webshop.webshop.shopping_cart.cart.update_cart", {
            item_code: itemCode,
            qty: qty,
        }).then(() => this.updateCartBadge());
    },

    /** Replay a basket filled before signing in into the real cart.
     *
     *  Runs once on the first page load after signing in. Quantities are
     *  added to whatever the account already had rather than replacing
     *  it, so someone who filled a basket on their phone and then signed
     *  in on a machine that already had one keeps both.
     *
     *  The local copy is cleared only once every item has been accepted;
     *  if the network fails halfway it stays put and is retried on the
     *  next page load, which is better than silently losing the basket.
     */
    mergeGuestCart() {
        if (this.isGuest) return Promise.resolve();

        const cart = this.guestCart();
        const codes = Object.keys(cart);
        if (!codes.length) return Promise.resolve();

        return codes
            .reduce(
                (chain, code) => chain.then(() =>
                    this.call("webshop.webshop.shopping_cart.cart.update_cart", {
                        item_code: code,
                        qty: parseInt(cart[code], 10) || 1,
                        with_items: 0,
                    })
                ),
                Promise.resolve()
            )
            .then(() => {
                this.clearGuestCart();
                this.updateCartBadge();
                this.toast(this.t("toast_cart_restored"), "success");
            })
            .catch(() => { /* kept for the next load */ });
    },

    /* ------------------------------------------------------------------
       Cart Badge — live count, from wherever this basket lives
       ------------------------------------------------------------------ */
    updateCartBadge() {
        const badge = document.getElementById("cart-badge");
        if (!badge) return;

        if (this.isGuest) {
            badge.textContent = this.guestCartCount();
            return;
        }

        this.call("webshop.webshop.shopping_cart.cart.get_cart_quotation")
            .then(data => {
                const items = (data && data.doc && data.doc.items) ? data.doc.items : [];
                const count = items.reduce((sum, item) => sum + (item.qty || 0), 0);
                badge.textContent = count;
            })
            .catch(() => {
                badge.textContent = "0";
            });
    },

    /* ------------------------------------------------------------------
       Toast notification
       ------------------------------------------------------------------ */
    toast(message, type = "info") {
        const container = document.getElementById("toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = "toast";
        const iconName = type === "success" ? "check-circle" : type === "error" ? "alert-circle" : "info";
        toast.innerHTML = `
            <i data-lucide="${iconName}" class="toast-icon"></i>
            <span>${message}</span>
        `;
        container.appendChild(toast);
        if (window.lucide) lucide.createIcons({ nodes: [toast] });

        setTimeout(() => {
            toast.classList.add("fade-out");
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    /* ------------------------------------------------------------------
       Mobile menu
       ------------------------------------------------------------------ */
    initMobileMenu() {
        const mobileBtn = document.getElementById("mobile-menu-btn");
        const navLinks = document.querySelector(".nav-links");

        if (!mobileBtn || !navLinks) return;

        // Ensure mobile backdrop exists
        let backdrop = document.getElementById("mobile-nav-backdrop");
        if (!backdrop) {
            backdrop = document.createElement("div");
            backdrop.id = "mobile-nav-backdrop";
            backdrop.className = "mobile-nav-backdrop";
            document.body.appendChild(backdrop);
        }

        const openMenu = () => {
            navLinks.classList.add("mobile-active");
            backdrop.classList.add("active");
            mobileBtn.setAttribute("aria-expanded", "true");
            document.body.style.overflow = "hidden";
            const iconMenu = mobileBtn.querySelector(".icon-menu");
            const iconX = mobileBtn.querySelector(".icon-x");
            if (iconMenu) iconMenu.style.display = "none";
            if (iconX) iconX.style.display = "block";
        };

        const closeMenu = () => {
            navLinks.classList.remove("mobile-active");
            backdrop.classList.remove("active");
            mobileBtn.setAttribute("aria-expanded", "false");
            document.body.style.overflow = "";
            const iconMenu = mobileBtn.querySelector(".icon-menu");
            const iconX = mobileBtn.querySelector(".icon-x");
            if (iconMenu) iconMenu.style.display = "block";
            if (iconX) iconX.style.display = "none";
        };

        mobileBtn.setAttribute("aria-label", "Toggle navigation menu");
        mobileBtn.setAttribute("aria-expanded", "false");

        mobileBtn.addEventListener("click", () => {
            if (navLinks.classList.contains("mobile-active")) {
                closeMenu();
            } else {
                openMenu();
            }
        });

        backdrop.addEventListener("click", closeMenu);

        navLinks.querySelectorAll("a").forEach(link => {
            link.addEventListener("click", closeMenu);
        });
    },

    escapeAttr(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    },

    escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    },

    stripHtml(html) {
        if (!html) return "";
        const tmp = document.createElement("div");
        tmp.innerHTML = html;
        return (tmp.textContent || tmp.innerText || "").trim();
    },

    /* ------------------------------------------------------------------
       Cart Drawer
       ------------------------------------------------------------------ */
    renderCartDrawer(options = {}) {
        const body = document.getElementById("cart-drawer-body");
        const subtotalEl = document.getElementById("drawer-subtotal");
        if (!body) return;

        if (options.customMessage) {
            body.innerHTML = options.customMessage;
            return;
        }

        body.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);">${this.t("loading")}</div>`;

        // A guest's basket lives in this browser and holds only codes and
        // quantities, so names and prices are fetched fresh each time.
        if (this.isGuest) {
            const cart = this.guestCart();
            const codes = Object.keys(cart);
            if (!codes.length) return this.paintDrawer(body, subtotalEl, []);

            this.call("custom_webshop.api.catalog.get_cart_preview", {
                item_codes: JSON.stringify(codes),
            })
                .then(rows => {
                    const known = {};
                    (rows || []).forEach(row => { known[row.item_code] = row; });

                    // Anything the shop no longer publishes is dropped
                    // rather than shown as a blank line.
                    let dropped = false;
                    codes.forEach(code => {
                        if (!known[code]) { delete cart[code]; dropped = true; }
                    });
                    if (dropped) this.saveGuestCart(cart);

                    this.paintDrawer(body, subtotalEl, Object.keys(cart).map(code => ({
                        item_code: code,
                        item_name: known[code].web_item_name || known[code].item_name || code,
                        image: known[code].image,
                        qty: cart[code],
                        rate: known[code].price,
                    })));
                    this.updateCartBadge();
                })
                .catch(() => {
                    body.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);">${this.t("error_generic")}</div>`;
                });
            return;
        }

        this.call("webshop.webshop.shopping_cart.cart.get_cart_quotation")
            .then(data => {
                const doc = data && data.doc;
                this.paintDrawer(body, subtotalEl, (doc && doc.items) ? doc.items : []);
            })
            .catch(() => {
                body.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);">${this.t("error_generic")}</div>`;
            });
    },

    /** Draw the drawer's contents.
     *
     *  Shared by both baskets, so a guest sees exactly the drawer a
     *  signed-in visitor sees - same rows, same controls, same subtotal.
     *  The quantity buttons are bound once and delegate to
     *  `updateDrawerQty`, which knows which basket to write to.
     */
    paintDrawer(body, subtotalEl, items) {
        if (!items.length) {
            body.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);">
                <i data-lucide="shopping-cart" style="width:40px;height:40px;margin-bottom:12px;opacity:0.3;"></i>
                <p>${this.t("cart_empty")}</p>
                <a href="/catalog" class="btn btn-secondary" style="margin-top:12px;">${this.t("cart_goto_shop")}</a>
            </div>`;
            if (subtotalEl) subtotalEl.textContent = "—";
            if (window.lucide) lucide.createIcons({ nodes: [body] });
            return;
        }

        let subtotal = 0;
        body.innerHTML = items.map(item => {
            const qty = item.qty || 1;
            const lineTotal = qty * (item.rate || 0);
            subtotal += lineTotal;
            const img = item.image || "/assets/custom_webshop/images/placeholder.jpg";
            const code = item.item_code || "";
            const name = item.item_name || code;
            return `
                <div class="drawer-item" data-item-code="${this.escapeAttr(code)}">
                    <img src="${img}" alt="${this.escapeAttr(name)}" class="drawer-item-img">
                    <div class="drawer-item-info">
                        <span class="drawer-item-name">${this.escapeAttr(name)}</span>
                        <div class="drawer-item-qty-row">
                            <button type="button" class="qty-btn drawer-qty-dec" aria-label="Decrease quantity">−</button>
                            <span class="qty-val">${qty}</span>
                            <button type="button" class="qty-btn drawer-qty-inc" aria-label="Increase quantity">+</button>
                        </div>
                    </div>
                    <div class="drawer-item-price">${parseFloat(lineTotal).toFixed(2)}</div>
                    <button type="button" class="remove-drawer-item-btn drawer-qty-remove" title="${this.t("btn_remove")}" aria-label="${this.t("btn_remove")}">
                        <i data-lucide="trash-2"></i>
                    </button>
                </div>`;
        }).join("");

        if (!body._drawerBound) {
            body.addEventListener("click", (e) => {
                const row = e.target.closest(".drawer-item");
                if (!row) return;
                const itemCode = row.dataset.itemCode;
                if (!itemCode) return;
                const qtyEl = row.querySelector(".qty-val");
                const currentQty = parseInt(qtyEl && qtyEl.textContent, 10) || 1;

                if (e.target.closest(".drawer-qty-remove")) {
                    window.updateDrawerQty(itemCode, 0);
                } else if (e.target.closest(".drawer-qty-dec")) {
                    window.updateDrawerQty(itemCode, currentQty - 1);
                } else if (e.target.closest(".drawer-qty-inc")) {
                    window.updateDrawerQty(itemCode, currentQty + 1);
                }
            });
            body._drawerBound = true;
        }

        if (subtotalEl) subtotalEl.textContent = subtotal.toFixed(2);
        if (window.lucide) lucide.createIcons({ nodes: [body] });
    },

    initCartDrawer(renderFn) {
        const cartToggle = document.getElementById("cart-toggle-btn");
        const closeBtn = document.getElementById("close-drawer-btn");
        const overlay = document.getElementById("cart-drawer-overlay");
        const drawer = document.getElementById("cart-drawer");

        const open = () => {
            if (typeof renderFn === "function") renderFn();
            if (drawer) drawer.classList.add("active");
            if (overlay) overlay.classList.add("active");
        };
        const close = () => {
            if (drawer) drawer.classList.remove("active");
            if (overlay) overlay.classList.remove("active");
        };

        if (cartToggle) cartToggle.addEventListener("click", open);
        if (closeBtn) closeBtn.addEventListener("click", close);
        if (overlay) overlay.addEventListener("click", close);

        // The one place an account becomes necessary. /cart redirects a
        // guest to sign-up on its own, so this is not the gate - it just
        // saves the round trip and makes the destination honest in the
        // status bar rather than looking like a dead link to the cart.
        const checkoutBtn = document.getElementById("drawer-checkout-btn");
        if (checkoutBtn) {
            if (this.isGuest) {
                checkoutBtn.href = "/login?redirect-to=" + encodeURIComponent("/cart");
            }
            checkoutBtn.addEventListener("click", close);
        }
    },

    /* ------------------------------------------------------------------
       Language toggle button wiring
       ------------------------------------------------------------------ */
    initLangToggle() {
        const langBtn = document.getElementById("lang-btn");
        if (!langBtn) return;
        langBtn.addEventListener("click", () => {
            this.applyLanguage(this.lang === "en" ? "ar" : "en");
        });
    },

    /* ------------------------------------------------------------------
       Theme toggle button wiring
       ------------------------------------------------------------------ */
    initThemeToggle() {
        const themeBtn = document.getElementById("theme-btn");
        if (!themeBtn) return;
        themeBtn.addEventListener("click", () => {
            this.applyTheme(this.theme === "dark" ? "light" : "dark");
        });
    },

    /* ------------------------------------------------------------------
       Navbar scroll shadow effect
       ------------------------------------------------------------------ */
    initNavbarScroll() {
        const navbar = document.querySelector(".navbar");
        if (!navbar) return;
        window.addEventListener("scroll", () => {
            if (window.scrollY > 20) {
                navbar.classList.add("scrolled");
            } else {
                navbar.classList.remove("scrolled");
            }
        }, { passive: true });
    },

    /* ------------------------------------------------------------------
       Initialize — call once on DOMContentLoaded
       Reads localStorage preferences, wires global UI, syncs cart badge
       ------------------------------------------------------------------ */
    init() {
        // Restore theme
        const savedTheme = localStorage.getItem("cnc_theme");
        if (savedTheme) this.applyTheme(savedTheme);

        // Restore language
        const savedLang = localStorage.getItem("cnc_lang_v2") || "ar";
        this.applyLanguage(savedLang);

        // Wire global controls
        this.initLangToggle();
        this.initThemeToggle();
        this.initMobileMenu();
        this.initNavbarScroll();

        // Mark session user — window.FRAPPE_SESSION injected by each page's Jinja
        if (window.FRAPPE_SESSION) {
            this.user = window.FRAPPE_SESSION.user || "Guest";
            this.csrfToken = window.FRAPPE_SESSION.csrf_token || "";
            this.isGuest = this.user === "Guest";
        }

        // Fallback to Frappe's live global (injected per-response via base template)
        if (!this.csrfToken && window.frappe && frappe.csrf_token) {
            this.csrfToken = frappe.csrf_token;
        }

        // Refresh token when returning from desk or another tab
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "visible" && window.frappe && frappe.csrf_token) {
                this.csrfToken = frappe.csrf_token;
            }
        });

        // Re-render lucide icons after page setup
        if (window.lucide) lucide.createIcons();

        // Sync cart badge, and hand over any basket filled before signing in.
        this.updateCartBadge();
        this.mergeGuestCart();
    }
};

/* Expose globally */
window.Store = Store;
window.t = (key, params) => Store.t(key, params);

window.updateDrawerQty = function(itemCode, qty) {
    const wanted = Math.max(0, qty);
    const done = () => {
        Store.updateCartBadge();
        Store.renderCartDrawer();
        if (wanted === 0) Store.toast(Store.t("toast_removed_cart"), "info");
    };

    // Whichever basket this visitor has, the buttons behave the same.
    if (Store.isGuest) {
        Store.setGuestQty(itemCode, wanted);
        done();
        return;
    }

    Store.call("webshop.webshop.shopping_cart.cart.update_cart", {
        item_code: itemCode,
        qty: wanted,
    })
        .then(done)
        .catch(err => Store.toast(err.message || Store.t("error_generic"), "error"));
};
