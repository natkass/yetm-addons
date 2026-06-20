# -*- coding: utf-8 -*-

from collections import OrderedDict
from operator import itemgetter

import base64
from odoo import http, _
from odoo.http import request
# from odoo.addons.website_portal.controllers.main import website_account
from odoo.addons.portal.controllers.portal import CustomerPortal as website_account
from odoo.tools import groupby as groupbyelem

from odoo.osv.expression import OR

class website_account(website_account):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'joborder_count' in counters:
            joborder_count = request.env['project.task'].sudo().search_count([
                ('job_partner_id','child_of', partner.id)
            ])
            values['joborder_count'] = joborder_count
        return values

    def _prepare_portal_layout_values(self):
        values = super(website_account, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        joborder_count = request.env['project.task'].sudo().search_count([('job_partner_id','child_of', partner.id)])
        values.update({
            'joborder_count': joborder_count,
        })
        return values

    @http.route(['/page/custom_job_workorder'], type='http', auth="public", website=True)
    def open_job_workorder(self, **post):
        return request.render("job_workorder_website_request.job_workorder")

    @http.route(['/job_order/workorder_submitted'], type='http', auth="public", methods=['POST'], website=True)
    def workorder_submitted(self, **post):
        vale = {
            'name': post.get('name'),
            'job_partner_name': post.get('your_name'),
            'job_partner_email': post.get('email'),
            'job_partner_phone': post.get('phone'),
            'description': post.get('description'),
            'priority': post.get('priority'),
            # 'user_id': False
            # 'activity_user_id': False
            # 'user_ids': False
        }
        if post.get('job_category') != 'Select category':
            vale.update({'job_category': post.get('job_category')})

        if request.env.user.has_group('base.group_public'):
            partner_id = request.env['res.partner'].sudo().search([('email', '=', post['email'])], limit=1)
        else:
            partner_id = request.env.user.partner_id
        # partner_id = request.env['res.partner'].sudo().search([('email', '=', post.get('email'))])
        if partner_id:
            vale.update({
                'job_partner_id': partner_id.id,
            })
        project_id = request.env['project.project'].sudo().search([('custom_code', '=', post.get('project_code'))], limit=1)
        if project_id:
            vale.update({
                'project_id': project_id.id,
                # 'user_id': project_id.user_id.id or False
                # 'activity_user_id': project_id.user_id.id or False
                'user_ids': [project_id.user_id.id] or False
            })
        workorder_id = request.env['project.task'].sudo().create(vale)
        # local_context = http.request.env.context.copy()
        # local_context.update({
        #     'partner_name':  post.get('your_name'),
        #     'email': post.get('email'),
        #     'subject': workorder_id.name,
        #     'job_number': workorder_id.job_number,
        # })
        issue_template = http.request.env.ref('job_workorder_website_request.email_template_job_order_custom')
        # issue_template.sudo().with_context(local_context).send_mail(request.uid, force_send=False)
        # issue_template.sudo().send_mail(request.uid, force_send=False)
        issue_template.sudo().send_mail(workorder_id.id, force_send=False)
        attachment_list = request.httprequest.files.getlist('attachment')
        if workorder_id and attachment_list:
            for image in attachment_list:
                if post.get('attachment'):
                    attachments = {
                               'res_name': image.filename,
                               'res_model': 'project.task',
                               'res_id': workorder_id,
                               'datas': base64.encodebytes(image.read()),
                               'type': 'binary',
                               #'datas_fname': image.filename,
                               'name': image.filename,
                           }
                    attachment_obj = http.request.env['ir.attachment']
                    attach = attachment_obj.sudo().create(attachments)
        if len(attachment_list) > 0:
            # group_msg = _('Customer has sent %s attachments to this joborder. Name of attachments are: ') % (len(attachment_list))
            group_msg = _('Customer has sent %s attachments on Job Order. Name of attachments are as below: ') % (len(attachment_list))
            for attach in attachment_list:
                group_msg = group_msg + '\n' + attach.filename
            # group_msg = group_msg + '\n'  +  '. You can see top attachment menu to download attachments.'
            group_msg = group_msg + '\n' + '. You can see the top attachment menu to download attachments.'
            workorder_id.sudo().message_post(body=group_msg,message_type='comment')
        values = {
            'order':workorder_id
        }
        return request.render('job_workorder_website_request.thanks_mail_send', values)

    @http.route(['/my/custom_joborders', '/my/custom_joborders/page/<int:page>'], type='http', auth="user", website=True)
    def my_joborders(self, page=1, date_begin=None, date_end=None, joborder=None, search=None, search_in='content', sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        domain = [('job_partner_id','child_of', partner.id)]
        
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'customer': {'input': 'customer', 'label': _('Search in Customer')},
            'stage': {'input': 'stage', 'label': _('Search in Stages')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }

        # archive groups - Default Group By 'create_date'
        # archive_groups = self._get_archive_groups('project.task', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, ['|', ('name', 'ilike', search), ('description', 'ilike', search)]])
            if search_in in ('customer', 'all'):
                search_domain = OR([search_domain, [('partner_id', 'ilike', search)]])
            if search_in in ('message', 'all'):
                search_domain = OR([search_domain, [('message_ids.body', 'ilike', search)]])
            if search_in in ('stage', 'all'):
                search_domain = OR([search_domain, [('stage_id', 'ilike', search)]])
            domain += search_domain

        
        pager = request.website.pager(
            url="/my/custom_joborder",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=values['joborder_count'],
            page=page,
            step=self._items_per_page
        )
        
        # content according to pager and archive selected
        
        job_order_ids = request.env['project.task'].sudo().search(domain, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'job_orders': job_order_ids,
            'page_name': 'portal_joborder',
            'default_url': '/my/custom_joborder',
            'pager': pager,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
        })
        return request.render("job_workorder_website_request.my_portal_job_order", values)
     
    # #@http.route(['/my/joborder/<int:joborder>'], type='http', auth="user", website=True)
    # @http.route(['/my/custom_joborder/<model("project.task"):joborder>'], type='http', auth="user", website=True)
    # def joborder_print(self, joborder, access_token=None, **kw):
    #     partner = request.env.user.partner_id
    #     if partner.commercial_partner_id != joborder.sudo().job_partner_id.commercial_partner_id:
    #         return request.redirect("/")
    #     else:
    #     # pdf, _ = request.env.ref('job_workorder_website_request.joborder_report').sudo().render_qweb_pdf(joborder.id)
    #         pdf, _ = request.env.ref('job_workorder_website_request.joborder_report').sudo()._render_qweb_pdf(joborder.id)
    #         pdfhttpheaders = [
    #             ('Content-Type', 'application/pdf'),
    #             ('Content-Length', len(pdf)),
    #         ]
    #         return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route(['/my/custom_joborder/<int:joborder>'], type='http', auth="user", website=True)
    def joborder_print(self, joborder, access_token=None, **kw):
       
        # pdf, _ = request.env.ref('job_workorder_website_request.joborder_report').sudo()._render_qweb_pdf([joborder])
        pdf, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf('job_workorder_website_request.joborder_report', [joborder])
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)


