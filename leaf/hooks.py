app_name = "leaf"
app_title = "Leaf ERP"
app_publisher = "Leaf"
app_description = "Leaf ERP Customizations and Email Alert Notifications"
app_email = "admin@leaf.hn"
app_license = "mit"

scheduler_events = {
    "daily": [
        "leaf.controllers.cai.check_cai_expiry_alerts"
    ]
}

after_migrate = [
    "leaf.setup_custom_fields.setup_custom_fields"
]

doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js"
}

