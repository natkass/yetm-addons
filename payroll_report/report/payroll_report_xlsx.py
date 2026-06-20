# from odoo import models
# import string
# import logging

# _logger = logging.getLogger(__name__)

# class payrollReportxls(models.AbstractModel):
#     _name = 'report.payroll_report.report_payroll_document'
#     _inherit = 'report.report_xlsx.abstract'

#     # def generate_xlsx_report(self, workbook, data, payroll):
        
#     #     _logger.info(f"insaid---------${payroll}")
#     #     for obj in payroll:
#     #         report_name = obj.name
#     #         # One sheet by partner
#     #         sheet = workbook.add_worksheet(report_name[:31])
#     #         bold = workbook.add_format({'bold': True})
#     #         sheet.write(0, 0, obj.name, bold)
#     def generate_xlsx_report(self, workbook, data, lines):
#         print("lines", lines)
#         _logger.info(f"===================lines===============${lines.slip_ids}")
#         format1 = workbook.add_format({'font_size':12, 'align': 'vcenter', 'bold': True, 'bg_color':'#d3dde3', 'color':'black', 'bottom': True, })
#         format2 = workbook.add_format({'font_size':12, 'align': 'vcenter', 'bold': True, 'bg_color':'#edf4f7', 'color':'black','num_format': '#,##0.00'})
#         format3 = workbook.add_format({'font_size':11, 'align': 'vcenter', 'bold': False, 'num_format': '#,##0.00'})
#         format3_colored = workbook.add_format({'font_size':11, 'align': 'vcenter', 'bg_color':'#f7fcff', 'bold': False, 'num_format': '#,##0.00'})
#         format4 = workbook.add_format({'font_size':12, 'align': 'vcenter', 'bold': True})
#         format5 = workbook.add_format({'font_size':12, 'align': 'vcenter', 'bold': False})
#        # sheet = workbook.add_worksheet('Payrlip Report')
        
#          # Fetch available salary rules:
#        # _logger.info(f"===================lines===============${lines.slip_ids.stract_id}")
#         used_structures = []
#         for sal_structure in lines.slip_ids.struct_id:
#             if sal_structure.id not in used_structures:
#                 used_structures.append([sal_structure.id,sal_structure.name])
#         _logger.info(f"===================used stracture===============${used_structures}")
#         # Logic for each workbook, i.e. group payslips of each salary structure into a separate sheet:
#         struct_count = 1
#         for used_struct in used_structures:
#             # Generate Workbook
#             sheet = workbook.add_worksheet(str(struct_count)+ ' - ' + str(used_struct[1]) )
#             cols = list(string.ascii_uppercase) + ['AA', 'AB', 'AC', 'AD', 'AE', 'AF', 'AG', 'AH', 'AI', 'AJ', 'AK', 'AL', 'AM', 'AN', 'AO', 'AP', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AV', 'AW', 'AX', 'AY', 'AZ']
#             rules = []
#             col_no = 2
#             # Fetch available salary rules:
#             for item in lines.slip_ids.struct_id.rule_ids:
#                 if item.struct_id.id == used_struct[0]:
#                     col_title = ''
#                     row = [None,None,None,None,None]
#                     row[0] = col_no
#                     row[1] = item.code
#                     row[2] = item.name
#                     col_title = str(cols[col_no]) + ':' + str(cols[col_no])
#                     row[3] = col_title
#                     if len(item.name) < 8:
#                         row[4] = 12
#                     else:
#                         row[4] = len(item.name) + 2
#                     rules.append(row)
#                     col_no += 1
#             # print('Salary rules to be considered for structure: ' + used_struct[1])
#             # print(rules)
            
#              #Report Details:
#             for item in lines.slip_ids:
#                 if item.struct_id.id == used_struct[0]:
#                     batch_period = str(item.date_from.strftime('%B %d, %Y')) + '  To  ' + str(item.date_to.strftime('%B %d, %Y'))
#                     company_name = item.company_id.name
#                     break
#             print(batch_period)
#             print(company_name)
        
#             #Company Name
#             sheet.write(0,0,company_name,format4)
    
#             sheet.write(0,2,'Payslip Period:',format4)
#             sheet.write(0,3,batch_period,format5)

#             sheet.write(1,2,'Payslip Structure:',format4)
#             sheet.write(1,3,used_struct[1],format5)
       
#             # List report column headers:
#             sheet.write(2,0,'Employee Name',format1)
#             sheet.write(2,1,'Department',format1)
#             for rule in rules:
#                 sheet.write(2,rule[0],rule[2],format1)

#             # Generate names, dept, and salary items:
#             x = 3
#             e_name = 3
#             has_payslips = False
#             for slip in lines.slip_ids:
#                 if lines.slip_ids:
#                     if slip.struct_id.id == used_struct[0]:
#                         has_payslips = True
#                         sheet.write(e_name, 0, slip.employee_id.name, format3)
#                         sheet.write(e_name, 1, slip.employee_id.department_id.name, format3)
#                         for line in slip.line_ids:
#                             for rule in rules:
#                                 if line.code == rule[1]:
#                                     if line.amount > 0:
#                                         sheet.write(x, rule[0], line.amount, format3_colored)
#                                     else:
#                                         sheet.write(x, rule[0], line.amount, format3)
#                         x += 1
#                         e_name += 1
#             # Generate summission row at report end:
#             sum_x = e_name
#             if has_payslips == True:
#                 sheet.write(sum_x,0,'Total',format2)
#                 sheet.write(sum_x,1,'',format2)
#                 for i in range(2,col_no):
#                     sum_start = cols[i] + '3'
#                     sum_end = cols[i] + str(sum_x)
#                     sum_range = '{=SUM(' + str(sum_start) + ':' + sum_end + ')}'
#                     # print(sum_range)
#                     sheet.write_formula(sum_x,i,sum_range,format2)
#                     i += 1
#             sheet.write(sum_x+2, 1, 'Prepared By', format1)
#             sheet.write(sum_x+2, 8, 'Checked By', format1)
#             sheet.write(sum_x+2, 12, 'Approved By', format1)

#             # set width and height of colmns & rows:
#             sheet.set_column('A:A',35)
#             sheet.set_column('B:B',20)
#             for rule in rules:
#                 sheet.set_column(rule[3],rule[4])
#             sheet.set_column('C:C',20)
#             struct_count += 1
        
        
from odoo import models
import string
import logging

_logger = logging.getLogger(__name__)

class payrollReportxls(models.AbstractModel):
    _name = 'report.payroll_report.report_payroll_document'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        # Log the initial lines data for debugging
        _logger.info(f"Generating report with lines: {lines}")
        print("lines", lines)

        # Define formats for the Excel report
        format1 = workbook.add_format({'font_size': 12, 'align': 'vcenter', 'bold': True, 'bg_color': '#d3dde3', 'color': 'black', 'bottom': True})
        format2 = workbook.add_format({'font_size': 12, 'align': 'vcenter', 'bold': True, 'bg_color': '#edf4f7', 'color': 'black', 'num_format': '#,##0.00'})
        format3 = workbook.add_format({'font_size': 11, 'align': 'vcenter', 'bold': False, 'num_format': '#,##0.00'})
        format3_colored = workbook.add_format({'font_size': 11, 'align': 'vcenter', 'bg_color': '#f7fcff', 'bold': False, 'num_format': '#,##0.00'})
        format4 = workbook.add_format({'font_size': 12, 'align': 'vcenter', 'bold': True})
        format5 = workbook.add_format({'font_size': 12, 'align': 'vcenter', 'bold': False})

        # Sort slip_ids alphabetically by employee name (case-insensitive, handle NULL values)
        sorted_slips = lines.slip_ids.sorted(key=lambda r: (r.employee_id.name or "").lower())
        _logger.info(f"Sorted slips by employee name: {[slip.employee_id.name for slip in sorted_slips[:5]]}...")  # Log first 5 for brevity

        # Fetch unique salary structures
        used_structures = []
        for sal_structure in sorted_slips.mapped('struct_id'):
            if sal_structure.id not in [x[0] for x in used_structures]:
                used_structures.append([sal_structure.id, sal_structure.name])
        _logger.info(f"Unique salary structures: {used_structures}")

        # Generate a separate sheet for each salary structure
        struct_count = 1
        for used_struct in used_structures:
            # Create worksheet with structure name and number
            sheet = workbook.add_worksheet(f"{struct_count} - {used_struct[1]}")
            cols = list(string.ascii_uppercase) + ['AA', 'AB', 'AC', 'AD', 'AE', 'AF', 'AG', 'AH', 'AI', 'AJ', 'AK', 'AL', 'AM', 'AN', 'AO', 'AP', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AV', 'AW', 'AX', 'AY', 'AZ']
            rules = []
            col_no = 2  # Start from column B (0 is A, 1 is B)

            # Fetch salary rules for the current structure
            for item in sorted_slips.mapped('struct_id.rule_ids'):
                if item.struct_id.id == used_struct[0]:
                    col_title = ''
                    row = [None, None, None, None, None]
                    row[0] = col_no
                    row[1] = item.code
                    row[2] = item.name
                    col_title = f"{cols[col_no]}:{cols[col_no]}"
                    row[3] = col_title
                    row[4] = max(12, len(item.name) + 2)  # Dynamic column width
                    rules.append(row)
                    col_no += 1

            # Get report details (period and company)
            batch_period = ""
            company_name = ""
            for slip in sorted_slips:
                if slip.struct_id.id == used_struct[0]:
                    batch_period = f"{slip.date_from.strftime('%B %d, %Y')} To {slip.date_to.strftime('%B %d, %Y')}"
                    company_name = slip.company_id.name
                    break

            _logger.info(f"Report details - Company: {company_name}, Period: {batch_period}")

            # Write report headers
            sheet.write(0, 0, company_name, format4)
            sheet.write(0, 2, 'Payslip Period:', format4)
            sheet.write(0, 3, batch_period, format5)
            sheet.write(1, 2, 'Payslip Structure:', format4)
            sheet.write(1, 3, used_struct[1], format5)

            # Write column headers
            sheet.write(2, 0, 'Employee Name', format1)
            sheet.write(2, 1, 'Department', format1)
            for rule in rules:
                sheet.write(2, rule[0], rule[2], format1)

            # Write employee data
            row = 3
            has_payslips = False
            for slip in sorted_slips:
                if slip.struct_id.id == used_struct[0]:
                    has_payslips = True
                    sheet.write(row, 0, slip.employee_id.name or "", format3)
                    sheet.write(row, 1, slip.employee_id.department_id.name or "", format3)
                    for line in slip.line_ids:
                        for rule in rules:
                            if line.code == rule[1]:
                                amount = line.amount or 0
                                cell_format = format3_colored if amount > 0 else format3
                                sheet.write(row, rule[0], amount, cell_format)
                    row += 1

            # Add totals row if there are payslips
            if has_payslips:
                sum_row = row
                sheet.write(sum_row, 0, 'Total', format2)
                sheet.write(sum_row, 1, '', format2)
                for i in range(2, col_no):
                    sum_start = f"{cols[i]}3"
                    sum_end = f"{cols[i]}{sum_row}"
                    sum_formula = f"=SUM({sum_start}:{sum_end})"
                    sheet.write_formula(sum_row, i, sum_formula, format2)

            # Add signatures
            sheet.write(sum_row + 2, 1, 'Prepared By', format1)
            sheet.write(sum_row + 2, 8, 'Checked By', format1)
            sheet.write(sum_row + 2, 12, 'Approved By', format1)

            # Set column widths
            sheet.set_column('A:A', 35)  # Employee Name
            sheet.set_column('B:B', 20)  # Department
            for rule in rules:
                sheet.set_column(rule[3], rule[4])  # Salary rules
            sheet.set_column('C:C', 20)  # Extra padding

            struct_count += 1

        _logger.info("Payroll report generation completed successfully.")
        