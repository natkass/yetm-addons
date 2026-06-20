{
    "name": "Foam Custom Product Creator",
    "version": "1.0",
    "depends": ["sale", "product"],
    "author": "Mahlet Woldeselassie",
    "category": "Sales",
    "summary": "Custom Foam Product Creation and Pricing",
    "description": "Compute and create foam products based on user input and add them to Sales Order lines.",
    "data": [
        "security/ir.model.access.csv",
        "views/foam_configurator_wizard_view.xml"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}
