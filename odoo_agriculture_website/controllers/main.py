# -*- coding: utf-8 -*-

from collections import OrderedDict
from operator import itemgetter

from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools import groupby as groupbyelem

from odoo.osv.expression import OR
from odoo import api, SUPERUSER_ID


class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        # values['crop_request_count'] = request.env['farmer.cropping.request'].sudo().search_count([('customer_id', '=', request.env.user.partner_id.id)])
        values['crop_request_count'] = request.env['farmer.cropping.request'].sudo().search_count([('customer_id', 'child_of', [request.env.user.partner_id.id])])
        values['page_name'] = 'crop_request_page'
        return values

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        crop_request_count = request.env['farmer.cropping.request'].sudo().search_count([('customer_id', 'child_of', [request.env.user.partner_id.id])])
        values.update({
            'crop_request_count': crop_request_count,
        })
        return values

    #open crop request form 
    @http.route('/page/crop_request', type='http', auth="user", website=True)
    def crop_request(self, **post):
        crops = request.env['farmer.location.crops'].sudo().search([])
        values = {
            'crops': crops,
        }
        return request.render('odoo_agriculture_website.crop_request',values)

    #open thanks form
    @http.route('/create_crop_request', type='http', auth="user", website=True)
    def create_crop_request(self, **post):
        crops = request.env['farmer.location.crops'].sudo().search([])
        customer = request.env.user.partner_id.id
        values = {
            'name':post['name'],
            'customer_id': customer,
            'phone': post['phone'],
            'email': post['email'],
            'start_date': post['start_date'],
            'end_date': post['end_date'],
            'description': post['description'],
            'crop_ids': post['crop_id'],
            # 'crop_request_count' : request.env['farmer.cropping.request'].sudo().search_count([]) #19/03/2020
        }
        # agri_group = request.env['res.groups'].sudo().search([('name','=', 'Agriculture Manager')])
        agri_group = request.env.ref('odoo_agriculture.group_agriculture_manager').sudo()
        custom_agri_user = agri_group.users and agri_group.users[0] and agri_group.users[0].id or SUPERUSER_ID
        values.update({
            'user_id': custom_agri_user ,
            'responsible_user_id': custom_agri_user
            })
        create_crops = http.request.env['farmer.cropping.request'].sudo().create(values)
        values.update({
            'user_id': request.env.user,
        })
        return request.render('odoo_agriculture_website.thanks_mail_sent',values)

    #open crop request list 
    @http.route(['/crop/request'], type='http', auth="user", website=True)
    def portal_request(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', groupby='project', **kw):
        values = self._prepare_portal_layout_values()
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Title'), 'order': 'name'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('customer_id', '=', request.env.user.partner_id.id)]},
        }
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'customer': {'input': 'customer', 'label': _('Search in Customer')},
            'stage': {'input': 'stage', 'label': _('Search in Stages')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'project': {'input': 'project', 'label': _('Project')},
        }
    
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain = searchbar_filters[filterby]['domain']

        crops = request.env['farmer.cropping.request'].sudo()
        # archive_groups = self._get_archive_groups(crops, domain)

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        if search and search_in:
            search_domain = []
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, ['|', ('name', 'ilike', search), ('description', 'ilike', search)]])
            domain += search_domain

        task_count = crops.search_count(domain)

        pager = portal_pager(
            url="/crop/request",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'search_in': search_in, 'search': search},
            total=task_count,
            page=page,
            step=self._items_per_page
        )
        tasks = crops.search(domain, order=order, limit=self._items_per_page, offset=(page - 1) * self._items_per_page)
        
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'requests': tasks,
            'page_name': 'crop_request_page',
            # 'archive_groups': archive_groups,
            'default_url': '/crop/request',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'crop_request_count': task_count,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("odoo_agriculture_website.crop_request_page", values)

    #open crop request form
    @http.route(['/crop/request/<int:crop_ids>'], type='http', auth="public", website=True)
    def portal_my_requests(self, crop_ids, access_token=None, **kw):
        partner = request.env.user.partner_id
        crop_id = request.env['farmer.cropping.request'].sudo().browse(crop_ids)
        if partner.commercial_partner_id.id != crop_id.customer_id.commercial_partner_id.id:
             return request.redirect("/")
        values = {'crop_request': crop_id}
        return request.render("odoo_agriculture_website.portal_my_crop_requests", values)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
