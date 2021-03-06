# -*- coding: utf-8 -*-
# * Copyright (C) 2012-2013 Croissance Commune
# * Authors:
#       * Arezki Feth <f.a@majerti.fr>;
#       * Miotte Julien <j.m@majerti.fr>;
#       * Pettier Gabriel;
#       * TJEBBES Gaston <g.t@majerti.fr>
#
# This file is part of Autonomie : Progiciel de gestion de CAE.
#
#    Autonomie is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Autonomie is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Autonomie.  If not, see <http://www.gnu.org/licenses/>.
#

"""
    Customer model : represents customers
    Stores the company and its main contact

    >>> from autonomie.models.customer import Customer
    >>> c = Customer()
    >>> c.contactLastName = u"Dupont"
    >>> c.contactFirstName = u"Jean"
    >>> c.name = u"Compagnie Dupont avec un t"
    >>> c.code = u"DUPT"
    >>> DBSESSION.add(c)

"""
import logging
import colander
import deform

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import (
    deferred,
)

from autonomie import forms
from autonomie.models.types import (
    CustomDateType,
    PersistentACLMixin,
)
from autonomie.models.utils import get_current_timestamp
from autonomie.models.base import (
    DBBASE,
    default_table_args,
    DBSESSION,
)

log = logging.getLogger(__name__)


def get_customers_from_request(request):
    if request.context.__name__ == 'company':
        return request.context.customers
    elif request.context.__name__ == 'customer':
        return [customer for customer in request.context.company.customers \
                if customer is not request.context]
    else:
        return []


@colander.deferred
def deferred_ccode_valid(node, kw):
    request = kw['request']
    customers = get_customers_from_request(request)

    def unique_ccode(node, value):
        """
            Test customer code unicity
        """
        if value.upper() in [customer.code.upper() for customer in customers]:
            raise colander.Invalid(
                node,
                u"Ce code est déjà utilisé pour identifier un autre client",
            )

    return colander.All(colander.Length(min=4, max=4), unique_ccode)


class Customer(DBBASE, PersistentACLMixin):
    """
        Customer model
        Stores the company and its main contact
        :param name: name of the company
        :param code: internal code of the customer (unique regarding the owner)
        :param multiline address: address of the company
        :param zipCode: zipcode of the company
        :param city: city
        :param country: country, default France
        :param contactLastName: lastname of the contact
        :param contactFirstName: firstname of the contact
        :param function: function of the contact
    """
    __tablename__ = 'customer'
    __table_args__ = default_table_args
    id = Column(
        'id',
        Integer,
        primary_key=True,
        info={
            'colanderalchemy': {
                'exclude': True,
                'title': u"Identifiant Autonomie",
            }
        },
    )

    created_at = deferred(
        Column(
            "creationDate",
            CustomDateType,
            default=get_current_timestamp,
            info={
                'export':{'exclude':True},
                'colanderalchemy': forms.EXCLUDED,
            },
        ),
        group='all',
    )

    updated_at = deferred(
        Column(
            "updateDate",
            CustomDateType,
            default=get_current_timestamp,
            onupdate=get_current_timestamp,
            info={
                'export':{'exclude':True},
                'colanderalchemy': forms.EXCLUDED,
            },
        ),
        group='all',
    )

    company_id = Column(
        "company_id",
        Integer,
        ForeignKey('company.id'),
        info={
            'export':{'exclude':True},
            'colanderalchemy': forms.EXCLUDED,
        }
    )

    name = Column(
        "name",
        String(255),
        info={
            "colanderalchemy": {
                'title': u'Nom',
            },
        },
        nullable=False,
    )

    code = Column(
        'code',
        String(4),
        info={
            'colanderalchemy':{
                'title': u"Code",
                'widget': deform.widget.TextInputWidget(mask='****'),
                'validator': deferred_ccode_valid,
            }
        },
        nullable=False,
    )

    contactLastName = deferred(
        Column(
            "contactLastName",
            String(255),
            info={
                "colanderalchemy": {
                    'title':u"Nom du contact principal",
                }
            },
            nullable=False,
        ),
        group='edit',
    )

    contactFirstName = deferred(
        Column(
            "contactFirstName",
            String(255),
            info={
                'colanderalchemy': {
                    'title': u"Prénom du contact principal",
                }
            },
            default="",
        ),
        group='edit',
    )

    function = deferred(
        Column(
            "function",
            String(255),
            info={
                'colanderalchemy': {
                    'title': u"Fonction du contact principal",
                }
            },
            default='',
        ),
        group="edit",
    )

    address = deferred(
        Column(
            "address",
            String(255),
            info={
                'colanderalchemy': {
                    'title': u'Adresse',
                    'widget': deform.widget.TextAreaWidget(
                        cols=25,
                        row=1,
                    )
                }
            },
            nullable=False,
        ),
        group='edit'
    )

    zipCode = deferred(
        Column(
            "zipCode",
            String(20),
            info={
                'colanderalchemy':{
                    'title': u'Code postal',
                },
            },
            nullable=False,
        ),
        group='edit',
    )

    city = deferred(
        Column(
            "city",
            String(255),
            info={
                'colanderalchemy': {
                    'title': u'Ville',
                }
            },
            nullable=False,
        ),
        group='edit',
    )

    country = deferred(
        Column(
            "country",
            String(150),
            info={
                'colanderalchemy': {'title': u'Pays'},
            },
            default=u'France',
        ),
        group='edit',
    )

    email = deferred(
        Column(
            "email",
            String(255),
            info={
                'colanderalchemy':{
                    'title': u"E-mail",
                    'validator': forms.mail_validator(),
                },
            },
            default='',
        ),
        group='edit',
    )

    phone = deferred(
        Column(
            "phone",
            String(50),
            info={
                'colanderalchemy': {
                    'title': u'Téléphone',
                },
            },
            default='',
        ),
        group='edit',
    )

    fax = deferred(
        Column(
            "fax",
            String(50),
            info={
                'colanderalchemy': {
                    'title': u'Fax',
                }
            },
            default='',
        ),
        group="edit"
    )

    intraTVA = deferred(
        Column(
            "intraTVA",
            String(50),
            info={
                'colanderalchemy': {'title': u"TVA intracommunautaire"},
            },
        ),
        group='edit',
    )

    comments = deferred(
        Column(
            "comments",
            Text,
            info={
                  'colanderalchemy':{
                      'title': u"Commentaires",
                      'widget': deform.widget.TextAreaWidget(
                          css_class="col-md-10"
                      ),
                  }
            },
        ),
        group='edit',
    )

    compte_cg = deferred(
        Column(
            String(125),
            info={
                'export': {'exclude': True},
                'colanderalchemy': {
                    'title': u"Compte CG",
                },
            },
            default="",
        ),
        group="edit",
    )

    compte_tiers = deferred(
        Column(
            String(125),
            info={
                'export': {'exclude': True},
                'colanderalchemy': {
                    'title': u"Compte tiers",
                }
            },
            default="",
        ),
        group="edit",
    )
    archived = Column(
        Boolean(),
        default=False,
        info={'colanderalchemy': forms.EXCLUDED},
    )


    def get_company_id(self):
        """
            :returns: the id of the company this customer belongs to
        """
        return self.company.id

    def todict(self):
        """
            :returns: a dict version of the customer object
        """
        projects = [project.todict() for project in self.projects]
        return dict(
            id=self.id,
            code=self.code,
            comments=self.comments,
            intraTVA=self.intraTVA,
            address=self.address,
            zipCode=self.zipCode,
            city=self.city,
            country=self.country,
            phone=self.phone,
            email=self.email,
            contactLastName=self.contactLastName,
            contactFirstName=self.contactFirstName,
            name=self.name,
            projects=projects,
            full_address=self.full_address,
            archived=self.archived,
        )

    def __json__(self, request):
        return self.todict()

    @property
    def full_address(self):
        """
            :returns: the customer address formatted in french format
        """
        address = u"{name}\n{address}\n{zipCode} {city}".format(name=self.name,
                address=self.address, zipCode=self.zipCode, city=self.city)
        if self.country not in ("France", "france"):
            address += u"\n{0}".format(self.country)
        return address

    def get_associated_tasks_by_type(self, type_str):
        """
        Return the tasks of type type_str associated to the current object
        """
        from autonomie.models.task import Task
        return DBSESSION().query(Task).filter_by(
            customer_id=self.id, type_=type_str
        ).all()

    @property
    def invoices(self):
        return self.get_associated_tasks_by_type('invoice')

    @property
    def estimations(self):
        return self.get_associated_tasks_by_type('estimation')

    @property
    def cancelinvoices(self):
        return self.get_associated_tasks_by_type('cancelinvoice')

    def has_tasks(self):
        from autonomie.models.task import Task
        num = DBSESSION().query(Task.id).filter_by(customer_id=self.id).count()
        return num > 0

    def is_deletable(self):
        """
            Return True if this project could be deleted
        """
        return self.archived and not self.has_tasks()


FORM_GRID = (
    ((4, True,), (2, True), ),
    ((4, True,), (4, True),  (4, True), ),
    ((4, True,), (2, True), (3, True), (3, True), ),
    ((4, True,), (4, True),  (4, True), ),
    ((3, True,), ),
    ((10, True,), ),
    ((3, True,), (3, True), ),
    )


