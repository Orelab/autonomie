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
    Task form schemas (estimation, invoice ...)
    Note : since deform doesn't fit our form needs
            (estimation form is complicated and its structure
             is mixing many sqla tables)

    validation process:
        set all the line in the colander expected schema
        validate
        raise error on an adapted way
            build an error dict which is mako understandable

    merging process:
        get the datas
        build a factory
        merge estimation and task object
        commit
        merge all lines
        commit
        merge payment conditions
        commit

    formulaire :

    phase, course, displayUnits
    lignes de prestation descr, cout qtité, unité, tva
    lignes de remise descr, cout, tva (seulement les tvas utilisées dans
                                                    les lignes au-dessus)
    TOTAL HT
    for tva in used_tva:
        TOTAL TVA tva%
    TTC
    Frais de port
    TOTAL
"""
import logging

import colander
import deform

from pyramid.security import has_permission
from deform_extensions import (
    GridMappingWidget,
)
from autonomie import forms
from autonomie.models.task import (
    WorkUnit,
    PaymentConditions,
)
from autonomie.models.tva import (
    Tva,
)
from .custom_types import (
    QuantityType,
    AmountType,
    Integer,
)


logger = logging.getLogger(__name__)
DAYS = (
    ('NONE', '-'),
    ('HOUR', u'Heure(s)'),
    ('DAY', u'Jour(s)'),
    ('WEEK', u'Semaine(s)'),
    ('MONTH', u'Mois'),
    ('FEUIL', u'Feuillet(s)'),
    ('PACK', u'Forfait'),
)


TASKTYPES_LABELS = {
    'invoice': u'Facture',
    u'estimation': u'Devis',
    'cancelinvoice': u'Avoir',
}


PAYMENTDISPLAYCHOICES = (
    ('NONE', u"Les paiments ne sont pas affichés dans le PDF",),
    ('SUMMARY', u"Le résumé des paiements apparaît dans le PDF",),
    ('ALL', u"Le détail des paiements apparaît dans le PDF",),
)


TEMPLATES_URL = 'autonomie:deform_templates/'


MAIN_INFOS_GRID = (
    (('name', 6), ('phase_id', 6),),
    (('taskDate', 6), ('financial_year', 6),),
    (('customer_id', 6), ('address', 6),),
    (('description', 12),),
    (('course', 12),),
    (('display_units', 12),),
)


def get_percents():
    """
        Return percents for select widget
    """
    percent_options = [(0, 'Aucun'), (5, '5%')]
    for i in range(10, 110, 10):
        percent_options.append((i, "%d %%" % i))
    return percent_options


def get_payment_times():
    """
        Return options for payment times select
    """
    payment_times = [(-1, u'Configuration manuelle')]
    for i in range(1, 12):
        payment_times.append((i, '%d fois' % i))
    return payment_times


def build_customer_value(customer=None):
    """
        return the tuple for building customer select
    """
    if customer:
        return (str(customer.id), customer.name)
    else:
        return ("", u"Sélectionner un client")


def build_customer_values(customers):
    """
        Build human understandable customer labels
        allowing efficient discrimination
    """
    options = [build_customer_value()]
    options.extend([build_customer_value(customer)
                    for customer in customers])
    return options


def get_customers_from_request(request):
    customers = []
    if request.context.__name__ == 'project':
        customers = request.context.customers
    elif request.context.__name__ in ('invoice', 'estimation', 'cancelinvoice'):
        if request.context.project is not None:
            customers = request.context.project.customers
    return customers


@colander.deferred
def deferred_customer_list(node, kw):
    request = kw['request']
    customers = get_customers_from_request(request)
    return deform.widget.Select2Widget(
        values=build_customer_values(customers),
        placeholder=u"Sélectionner un client",
    )


@colander.deferred
def deferred_customer_validator(node, kw):
    request = kw['request']
    customers = get_customers_from_request(request)
    customer_ids = [customer.id for customer in customers]

    def customer_oneof(value):
        if value in ("0", 0):
            return u"Veuillez choisir un client"
        elif value not in customer_ids:
            return u"Entrée invalide"
        return True
    return colander.Function(customer_oneof)


def get_tasktype_from_request(request):
    route_name = request.matched_route.name
    for predicate in ('estimation', 'invoice', 'cancelinvoice'):
        # Matches estimation and estimations
        if route_name in [predicate, "project_%ss" % (predicate,)]:
            return predicate
    raise Exception(u"You shouldn't have come here with the current route %s"
                    % route_name)


@colander.deferred
def deferred_course_title(node, kw):
    """
        deferred title
    """
    request = kw['request']
    tasktype = get_tasktype_from_request(request)
    if tasktype == "invoice":
        return u"Cette facture concerne-t-elle une formation professionnelle \
continue ?"
    elif tasktype == "cancelinvoice":
        return u"Cet avoir concerne-t-il une formation professionnelle \
continue ?"

    elif tasktype == "estimation":
        return u"Ce devis concerne-t-il une formation professionnelle \
continue ?"


def get_tva_choices():
    """
        Return data structure for tva select widget options
    """
    return [(unicode(tva.value), tva.name)for tva in Tva.query()]


def get_unities():
    unities = ["", ]
    unities.extend([workunit.label for workunit in WorkUnit.query()])
    return unities


@colander.deferred
def deferred_unity_widget(node, kw):
    unities = get_unities()
    return deform.widget.SelectWidget(values=zip(unities, unities))


def _is_in(datas):
    def func(value):
        return value in datas
    return func


@colander.deferred
def deferred_unity_validator(node, kw):
    return colander.OneOf(get_unities())


@colander.deferred
def deferred_tva_validator(node, kw):
    options = [int(option[0]) for option in get_tva_choices()]
    return colander.Function(_is_in(options))


@colander.deferred
def deferred_tvas_widget(node, kw):
    """
        return a tva widget
    """
    tvas = get_tva_choices()
    wid = deform.widget.SelectWidget(values=tvas)
    return wid


@colander.deferred
def deferred_default_tva(node, kw):
    """
        return a tva widget
    """
    default_tva = Tva.get_default()
    if default_tva is not None:
        return unicode(default_tva.value)
    else:
        return colander.null


@colander.deferred
def deferred_default_phase(node, kw):
    """
        Return the default phase if one is present in the request arguments
    """
    request = kw['request']
    phases = get_phases_from_request(request)
    phase = request.params.get('phase')
    if phase in [str(p.id) for p in phases]:
        return int(phase)
    else:
        return colander.null


def get_phase_choices(phases):
    """
        Return data structure for phase select options
    """
    return ((phase.id, phase.name) for phase in phases)


def get_phases_from_request(request):
    """
        Get the phases from the current project regarding request context
    """
    phases = []
    if request.context.__name__ == 'project':
        phases = request.context.phases
    elif request.context.__name__ in ('invoice', 'cancelinvoice', 'estimation'):
        phases = request.context.project.phases
    return phases


@colander.deferred
def deferred_default_name(node, kw):
    """
    Return a default name for the new document
    """
    request = kw['request']
    tasktype = get_tasktype_from_request(request)
    method = "get_next_{0}_number".format(tasktype)

    if request.context.__name__ == 'project':
        # e.g : project.get_next_invoice_number()
        number = getattr(request.context, method)()

        name = TASKTYPES_LABELS[tasktype] + ' %s' % number
    else:
        # Unusefull
        name = request.context.name
    return name


@colander.deferred
def deferred_phases_widget(node, kw):
    """
        return phase select widget
    """
    request = kw['request']
    phases = get_phases_from_request(request)
    choices = get_phase_choices(phases)
    wid = deform.widget.SelectWidget(values=choices)
    return wid


@colander.deferred
def deferred_default_payment_condition(node, kw):
    entry = PaymentConditions.query().filter(
        PaymentConditions.default == True #  noqa
    ).first()
    if entry is not None:
        return entry.label
    else:
        return ""


class TaskLine(colander.MappingSchema):
    """
        A single estimation line
    """
    description = forms.textarea_node(
        title=u"Prestation",
        missing=u'',
        richwidget=True,
        richtext_options={"height": "100px"},
        css_class='col-md-3',
    )
    cost = colander.SchemaNode(
        AmountType(),
        title=u"Prix/unité",
        widget=deform.widget.TextInputWidget(),
        css_class='col-md-1')
    group_quantity = colander.SchemaNode(
        colander.Float(),
        widget=deform.widget.HiddenWidget(),
        default=0
    )
    quantity = colander.SchemaNode(
        QuantityType(),
        title=u"Quantité",
        widget=deform.widget.TextInputWidget(),
        validator=forms.positive_validator,
        css_class='col-md-1')
    unity = colander.SchemaNode(
        colander.String(),
        title=u"Unité",
        widget=deferred_unity_widget,
        validator=deferred_unity_validator,
        missing=u"",
        css_class='col-md-2')
    tva = colander.SchemaNode(
        Integer(),
        widget=deferred_tvas_widget,
        default=deferred_default_tva,
        validator=deferred_tva_validator,
        css_class='col-md-1',
        title=u'TVA')


class DiscountLine(colander.MappingSchema):
    """
        A single estimation line
    """
    description = forms.textarea_node(
        missing=u'',
        title=u"Remise",
        richwidget=True,
        richtext_options={"height": "100px"},
        css_class='col-md-4',
    )
    amount = colander.SchemaNode(
        AmountType(),
        title=u"Montant",
        widget=deform.widget.TextInputWidget(),
        css_class='col-md-1',
        validator=forms.positive_validator,
    )
    tva = colander.SchemaNode(
        Integer(),
        title=u'TVA',
        widget=deferred_tvas_widget,
        default=deferred_default_tva,
        css_class='col-md-2 col-md-offset-3',
    )


class TaskLines(colander.SequenceSchema):
    """
        Sequence of task lines
    """
    taskline = TaskLine(
        widget=deform.widget.MappingWidget(
            template=TEMPLATES_URL + 'inline_mapping.pt',
            item_template=TEMPLATES_URL + 'inline_mapping_item.pt',
            item_css_class="taskline",
        )
    )


class DiscountLines(colander.SequenceSchema):
    """
        Sequence of discount lines
    """
    discountline = DiscountLine(
        widget=deform.widget.MappingWidget(
            template=TEMPLATES_URL + 'inline_mapping.pt',
            item_template=TEMPLATES_URL + 'inline_mapping_item.pt',
            item_css_class="discountline",
        ),
    )


class TaskLineGroupMapping(colander.MappingSchema):
    title = colander.SchemaNode(colander.String(), title=u"Titre de l'ouvrage")
    description = forms.textarea_node(
        title=u"Description",
        missing=u'',
        richwidget=False,
        richtext_options={"height": "100px"},
    )
    display_details = colander.SchemaNode(
        colander.Boolean(),
        title=u"Afficher les détails de l'ouvrage",
        description=u"Les prestations composant l'ouvrage doivent-elles être \
affichées dans la sortie PDF ?",
        default=False,
        missing=False,
    )
    quantity = colander.SchemaNode(
        colander.Float(),
        title=u"Quantité",
        description=u"Les prestations de cet ouvrage issues du catalogue \
produit verront leur quantité augmenté en conséquence",
        widget=deform.widget.TextInputWidget(
            template=TEMPLATES_URL + 'number_input.pt',
        ),
        default=1,
    )
    lines = TaskLines(
        widget=deform.widget.SequenceWidget(
            template=TEMPLATES_URL + 'tasklines_sequence.pt',
            add_subitem_text_template=u"Ajouter une prestation à cet ouvrage",
            orderable=True,
        ),
        title=u'',
    )


class TaskLineGroupSeq(colander.SequenceSchema):
    groups = TaskLineGroupMapping(
        title=u"Ouvrage",
        widget=deform.widget.MappingWidget(
            template=TEMPLATES_URL + 'groupline_mapping.pt',
        ),
    )


class TaskLinesBlock(colander.MappingSchema):
    """
        Fieldset containing the "Détail de la prestation" block
        with estimation and invoice lines and all the stuff
    """
    lines = TaskLines(
        widget=deform.widget.SequenceWidget(
            template=TEMPLATES_URL + 'tasklines_sequence.pt',
            orderable=True,
            add_subitem_text_template=u"Ajouter une prestation",
        ),
        title=u'',
    )
    groups = TaskLineGroupSeq(
        widget=deform.widget.SequenceWidget(
            template=TEMPLATES_URL + 'grouplines_sequence.pt',
            add_subitem_text_template=u"Ajouter un ouvrage",
            item_template=TEMPLATES_URL + 'grouplines_sequence_item.pt',
        ),
        title=u"",
    )
    discounts = DiscountLines(
        widget=deform.widget.SequenceWidget(
            template=TEMPLATES_URL + 'discountlines_sequence.pt',
            orderable=True,
            add_subitem_text_template=u"Ajouter une remise",
        ),
        title=u'',
    )
    expenses_ht = colander.SchemaNode(
        AmountType(),
        widget=deform.widget.TextInputWidget(
            template=TEMPLATES_URL + 'wrappable_input.pt',
            after=TEMPLATES_URL + 'tvalist.pt',
            after_options={'label': u'Montant TVA', 'id': 'tvapart'},
        ),
        title=u"Frais forfaitaires (HT)",
        missing=0,
        validator=forms.positive_validator,
    )

    default_tva = colander.SchemaNode(
        colander.Integer(),
        title=u"",
        widget=deform.widget.HiddenWidget(),
        default=deferred_default_tva,
    )


class TaskConfiguration(colander.MappingSchema):
    """
        Main fields to be configured
    """
    name = colander.SchemaNode(
        colander.String(),
        title=u"Libellé du document",
        validator=colander.Length(max=255),
        default=deferred_default_name,
        missing="",
        )
    customer_id = colander.SchemaNode(
        colander.Integer(),
        title=u"Choix du client",
        widget=deferred_customer_list,
        validator=deferred_customer_validator
        )
    address = forms.textarea_node(
        title=u"Nom et adresse du client",
        widget_options={'rows': 4}
    )
    phase_id = colander.SchemaNode(
        colander.String(),
        title=u"Phase où insérer le devis",
        widget=deferred_phases_widget,
        default=deferred_default_phase
        )
    taskDate = forms.today_node(title=u"Date du devis")
    description = forms.textarea_node(title=u"Objet du devis")
    course = colander.SchemaNode(
        colander.Integer(),
        title=u"",
        label=deferred_course_title,
        widget=deform.widget.CheckboxWidget(true_val="1", false_val="0"),
        missing=0,
    )
    display_units = colander.SchemaNode(
        colander.Integer(),
        title="",
        label=u"Afficher le détail des prestations dans la sortie PDF ?",
        widget=deform.widget.CheckboxWidget(true_val="1", false_val="0"),
        missing=0,
    )


class TaskNotes(colander.MappingSchema):
    """
        Notes
    """
    exclusions = forms.textarea_node(
        title=u'Notes',
        missing=u"",
        description=u"Note complémentaires concernant les prestations décrites"
    )


class TaskCommunication(colander.MappingSchema):
    """
        Communication avec la CAE
    """
    statusComment = forms.textarea_node(
        title=u'',
        missing=u'',
        description=u"Message à destination des membres de la CAE qui \
valideront votre document (n'apparaît pas dans le PDF)",
    )


class TaskSchema(colander.Schema):
    """
        colander base Schema for task edition
    """
    common = TaskConfiguration(
        title=u"",
        widget=GridMappingWidget(named_grid=MAIN_INFOS_GRID),
    )
    lines = TaskLinesBlock(
        title=u"Détail des prestations",
        widget=deform.widget.MappingWidget(
            item_template=TEMPLATES_URL + 'taskdetails_mapping_item.pt'
        )
    )
    communication = TaskCommunication(title=u"Communication Entrepreneur/CAE")


def remove_admin_fields(schema, kw):
    request = kw['request']
    context = request.context

    doctype = schema['lines']['lines'].doctype
    lines = schema['lines']['lines']
    glines = schema['lines']['groups']['groups']['lines']
    glines.doctype = doctype
    for schema_node in (lines, glines):
        if not has_permission("task.admin", context, request):
            # Non admin users doesn't edit products
            if doctype != 'estimation':
                del schema_node['taskline']['product_id']
            schema_node.is_admin = False
            schema_node['taskline']['description'].css_class = 'col-md-4'
            schema_node['taskline']['tva'].css_class = 'col-md-2'
        else:
            schema_node.is_admin = True
            if doctype != 'estimation':
                schema_node['taskline']['description'].css_class = 'col-md-3'
                schema_node['taskline']['tva'].css_class = 'col-md-1'
            else:
                schema_node['taskline']['description'].css_class = 'col-md-4'
                schema_node['taskline']['tva'].css_class = 'col-md-2'


TASKSCHEMA = TaskSchema(after_bind=remove_admin_fields)


class EstimationPaymentLine(colander.MappingSchema):
    """
        Payment line
    """
    description = colander.SchemaNode(
        colander.String(),
        default=u"Solde",
    )
    paymentDate = forms.today_node()
    amount = colander.SchemaNode(AmountType(), default=0)


class EstimationPaymentLines(colander.SequenceSchema):
    """
        Sequence of payment lines
    """
    line = EstimationPaymentLine(widget=deform.widget.MappingWidget())


class EstimationPayments(colander.MappingSchema):
    """
        Gestion des acomptes
    """
    deposit = colander.SchemaNode(
        colander.Integer(),
        title=u"Acompte à la commande",
        default=0,
        widget=deform.widget.SelectWidget(
            values=get_percents(),
            css_class='col-md-2')
    )
    payment_times = colander.SchemaNode(
        colander.Integer(),
        title=u"Paiement en ",
        default=1,
        widget=deform.widget.SelectWidget(
            values=get_payment_times(),
            css_class='col-md-2'
        )
    )
    paymentDisplay = colander.SchemaNode(
        colander.String(),
        validator=colander.OneOf([x[0] for x in PAYMENTDISPLAYCHOICES]),
        widget=deform.widget.RadioChoiceWidget(values=PAYMENTDISPLAYCHOICES),
        title=u"Affichage des paiements",
        default="SUMMARY")
    payment_lines = EstimationPaymentLines(
        widget=deform.widget.SequenceWidget(
            template=TEMPLATES_URL + 'paymentlines_sequence.pt',
            item_template=TEMPLATES_URL + 'paymentlines_sequence_item.pt',
            min_len=1),
        title=u'',
        description=u"Définissez les échéances de paiement")

    payment_conditions_select = colander.SchemaNode(
        colander.String(),
        widget=forms.get_deferred_select(PaymentConditions),
        title=u"Conditions de paiement prédéfinies",
        missing=colander.drop,
    )

    payment_conditions = forms.textarea_node(
        title=u"Conditions de paiement",
        default=deferred_default_payment_condition,
    )


def get_estimation_schema():
    """
        Return the schema for estimation add/edit
    """
    schema = TASKSCHEMA.clone()
    schema['lines']['lines'].doctype = "estimation"
    tmpl = 'autonomie:deform_templates/paymentdetails_item.pt'
    schema.add_before(
        'communication',
        TaskNotes(title=u"Notes", name="notes"),
    )
    schema.add_before(
        'communication',
        EstimationPayments(
            title=u'Conditions de paiement',
            widget=deform.widget.MappingWidget(
                item_template=tmpl
            ),
            name='payments',
        )
    )
    return schema


#  Dans le formulaire de création de devis par exemple, on trouve
#  aussi bien des TaskLine que des Estimation ou des DiscountLine et leur
#  configuration est imbriquée. On a donc besoin de faire un mapping d'un
#  dictionnaire contenant les modèles {'estimation':..., 'tasklines':...}
#  vers un dictionnaire correspondant au formulaire en place.
TASK_MATCHING_MAP = (
    ('name', 'common'),
    ('phase_id', 'common'),
    ('taskDate', 'common'),
    ('financial_year', 'common'),
    ('description', 'common'),
    ('customer_id', 'common'),
    ('address', 'common'),
    ('course', 'common'),
    ('display_units', 'common'),
    ('expenses_ht', 'lines'),
    ('exclusions', 'notes'),
    ('payment_conditions', 'payments'),
    ('statusComment', 'communication'),
    ('paymentDisplay', 'payments'),
)


def dbdatas_to_appstruct(dbdatas, matching_map=TASK_MATCHING_MAP):
    """
    convert db dict fashionned datas to the appropriate sections
    to fit the form schema
    """
    appstruct = {}
    for field, section in matching_map:
        value = dbdatas.get(field)
        if value is not None:
            appstruct.setdefault(section, {})[field] = value
    return appstruct


def appstruct_to_dbdatas(appstruct, matching_map=TASK_MATCHING_MAP):
    """
    convert colander deserialized datas to database dbdatas
    """
    dbdatas = {'task': {}}
    task_datas = dbdatas['task']
    for field, section in matching_map:
        value = appstruct.get(section, {}).get(field, None)
        if value not in (None, colander.null):
            task_datas[field] = value
    return dbdatas


def get_lines_block_appstruct(appstruct, dbdatas):
    """
    Return the appstruct relatd to the task lines block of the the Task Schema

    the task lines block groups :
        task lines
        task lines groups
        discount lines

    :param dbdatas: Datas coming from the database in dict format
    """
    appstruct.setdefault('lines', {})

    for key in ('lines', 'groups', "discounts"):
        if key in dbdatas:
            appstruct['lines'][key] = dbdatas[key]

    return appstruct


def add_order_to_lines(appstruct):
    """
    add the order of the different lines coming from a submitted form
    """
    tasklines = appstruct.get('lines', {})

    lines = tasklines.get('lines', [])
    for index, line in enumerate(lines):
        line['order'] = index + 1

    groups = tasklines.get('groups', [])
    for index, group in enumerate(groups):
        group['order'] = index + 1
        for jindex, line in enumerate(group.get('lines', [])):
            line['order'] = jindex + 1

    payment_lines = appstruct.get('payments', {}).get('payment_lines', [])
    for index, line in enumerate(payment_lines):
        line['order'] = index + 1

    return appstruct


def get_estimation_appstruct(dbdatas):
    """
        return EstimationSchema-compatible appstruct
    """
    appstruct = dbdatas_to_appstruct(dbdatas)

    if "payment_lines" in dbdatas:
        appstruct.setdefault('payments', {})['payment_lines'] = \
            dbdatas['payment_lines']
    appstruct = get_lines_block_appstruct(appstruct, dbdatas)
    appstruct = add_payment_block_appstruct(appstruct, dbdatas)
    appstruct = add_notes_block_appstruct(appstruct, dbdatas)
    return appstruct


def get_estimation_dbdatas(appstruct):
    """
        return dict with db compatible datas
    """
    dbdatas = appstruct_to_dbdatas(appstruct)

    # Estimation specific keys
    for key in ('paymentDisplay', 'deposit', ):
        dbdatas['task'][key] = appstruct['payments'][key]
    dbdatas.update(appstruct['notes'])

    add_order_to_lines(appstruct)
    dbdatas['lines'] = appstruct['lines']['lines']
    dbdatas['groups'] = appstruct['lines']['groups']
    dbdatas['discounts'] = appstruct['lines']['discounts']
    dbdatas['payment_lines'] = appstruct['payments']['payment_lines']
    dbdatas = set_manualDeliverables(appstruct, dbdatas)
    return dbdatas


def get_invoice_appstruct(dbdatas):
    """
        return InvoiceSchema compatible appstruct
    """
    appstruct = dbdatas_to_appstruct(dbdatas)
    appstruct = get_lines_block_appstruct(appstruct, dbdatas)
    return appstruct


def get_invoice_dbdatas(appstruct):
    """
        return dict with db compatible datas
    """
    dbdatas = appstruct_to_dbdatas(appstruct)

    add_order_to_lines(appstruct)
    dbdatas['lines'] = appstruct['lines']['lines']
    dbdatas['groups'] = appstruct['lines']['groups']
    dbdatas['discounts'] = appstruct['lines']['discounts']
    return dbdatas


def get_cancel_invoice_appstruct(dbdatas):
    """
        return cancel invoice schema compatible appstruct
    """
    appstruct = dbdatas_to_appstruct(dbdatas)
    appstruct = get_lines_block_appstruct(appstruct, dbdatas)
    return appstruct


def get_cancel_invoice_dbdatas(appstruct):
    """
        return dict with db compatible datas
    """
    dbdatas = appstruct_to_dbdatas(appstruct)

    add_order_to_lines(appstruct)
    dbdatas['lines'] = appstruct['lines']['lines']
    dbdatas['groups'] = appstruct['lines']['groups']
    return dbdatas


def set_manualDeliverables(appstruct, dbdatas):
    """
        Hack the dbdatas to set the manualDeliverables value
    """
    # On s'assure que la clé task existe et on set le manualDeliverables par
    # défaut
    dbdatas.setdefault('task', {})['manualDeliverables'] = 0

    # dans l'interface payment_times == -1 correspond à Configuration Manuelle
    # des paiements
    payment_times = appstruct.get('payments', {}).get('payment_times')
    if payment_times == -1:
        dbdatas['task']['manualDeliverables'] = 1
    return dbdatas


def add_payment_block_appstruct(appstruct, dbdatas):
    """
        Hack the appstruct to set the payment informations values
    """
    if dbdatas.get('manualDeliverables') == 1:
        # dans l'interface payment_times == -1 correspond à Configuration
        # Manuelle des paiements
        appstruct.setdefault('payments', {})['payment_times'] = -1
    else:
        appstruct.setdefault(
            'payments', {}
        )['payment_times'] = max(1, len(dbdatas.get('payment_lines')))

    appstruct['payments']['paymentDisplay'] = dbdatas['paymentDisplay']
    appstruct['payments']['deposit'] = dbdatas['deposit']
    return appstruct


def add_notes_block_appstruct(appstruct, dbdatas):
    """
    Fill the notes block
    """
    appstruct.setdefault(
        'notes', {
        })['exclusions'] = dbdatas.get('exclusions', '')
    return appstruct
