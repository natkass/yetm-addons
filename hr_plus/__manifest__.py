{
    'name': 'HR Plus',
    'version': '1.0',
    'summary': 'Manages Overtime and integrates with Payroll',
    'author': '1514',
    'category': 'Human Resources',
    'depends': ['mail','hr', 'hr_payroll', 'report_xlsx'],
    'data': [        
        'security/hr_groups.xml',
        'security/ir.model.access.csv',
        
        'security/hr_rules.xml',

        'data/sequence.xml',        
        'data/input_types.xml',


        'views/hr_plus_views.xml',        
        'views/hr_overtime_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_incentive_views.xml',
        'views/hr_perdiem_views.xml',
        'views/hr_penalty_views.xml',
        'views/hr_loan_views.xml',
        'views/hr_advance_views.xml',

        'wizard/hr_advance_report_wizard_views.xml',
        'wizard/hr_loan_installment_report_wizard.xml',
        
        
        
    ],
    
    'installable': True,
    'application': True,
}
