# -*- coding: utf-8 -*-
# * File Name :
#
# * Copyright (C) 2010 Gaston TJEBBES <g.t@majerti.fr>
# * Company : Majerti ( http://www.majerti.fr )
#
#   This software is distributed under GPLV3
#   License: http://www.gnu.org/licenses/gpl-3.0.txt
#
# * Creation Date : 10-04-2012
# * Last Modified :
#
# * Project :
#
"""
    User account handling form schemas
"""
import colander
import logging

from deform import widget

from autonomie.models.user import User
from autonomie.models.company import Company
from autonomie.views.forms.widgets import get_mail_input
from autonomie.views.forms.widgets import deferred_edit_widget
from autonomie.utils.security import MANAGER_ROLES
from autonomie.utils.security import ADMIN_ROLES

log = logging.getLogger(__name__)


def unique_login(node, value):
    """
        Test login unicity against database
    """
    result = User.query().filter_by(login=value).first()
    if result:
        message = u"Le login '{0}' n'est pas disponible.".format(
                                                            value)
        raise colander.Invalid(node, message)


def auth(form, value):
    """
        Check the login/password content
    """
    log.debug(u" * Authenticating")
    login = value.get('login')
    log.debug(u"   +  Login {0}".format(login))
    password = value.get('password')
    result = User.query().filter_by(login=login).first()
    if not result or not result.auth(password):
        log.debug(u"    - Authentication Error")
        message = u"Erreur d'authentification"
        exc = colander.Invalid(form, message)
        exc['password'] = message
        raise exc


@colander.deferred
def deferred_login_validator(node, kw):
    """
        Dynamically choose the validator user for validating the login
    """
    if not kw.get('edit'):
        return unique_login
    return None


@colander.deferred
def deferred_pwd_validator(node, kw):
    """
        Returns auth func if check is True in the binding parameters
    """
    if kw.get('check'):
        return auth
    else:
        return None


@colander.deferred
def deferred_company_input(node, kw):
    """
        Deferred company list
    """
    companies = kw.get('companies')
    wid = widget.AutocompleteInputWidget(values=companies,
            template="autonomie:deform_templates/autocomple_input.pt")
    return wid


@colander.deferred
def deferred_missing_password(node, kw):
    """
        deferred missing password
    """
    if kw.get('edit'):
        return ""
    else:
        return colander.required


def get_companies_choices():
    """
        Return companies choices for autocomplete
    """
    return [comp.name for comp in Company.query([Company.name]).all()]


class AccountSchema(colander.MappingSchema):
    """
        Form Schema for an account creation
    """
    login = colander.SchemaNode(
        colander.String(),
        title=u"Identifiant",
        validator=deferred_login_validator,
        widget=deferred_edit_widget)
    firstname = colander.SchemaNode(
        colander.String(),
        title=u"Prénom")
    lastname = colander.SchemaNode(
        colander.String(),
        title=u"Nom")
    email = get_mail_input(missing=u"")
    code_compta = colander.SchemaNode(
        colander.String(),
        title=u"Code compta",
        description=u"Code comptabilité utilisé dans Sage",
        missing="")
    primary_group = colander.SchemaNode(
        colander.String(),
        title=u"Rôle de l'utilisateur",
        validator=colander.OneOf([x[0] for x in ADMIN_ROLES]),
        widget=widget.RadioChoiceWidget(values=ADMIN_ROLES),
        default=u"3")


class PasswordChangeSchema(colander.MappingSchema):
    """
        Password modification form
    """
    login = colander.SchemaNode(
        colander.String(),
        widget=widget.HiddenWidget()
    )
    password = colander.SchemaNode(
        colander.String(),
        widget=widget.PasswordWidget(),
        title="Mot de passe actuel",
        default=u'')
    pwd = colander.SchemaNode(
        colander.String(),
        widget=widget.CheckedPasswordWidget(),
        title="Nouveau mot de passe")


class CompanySchema(colander.SequenceSchema):
    company = colander.SchemaNode(
        colander.String(),
        title=u"Nom de l'entreprise",
        widget=deferred_company_input)


class Password(colander.MappingSchema):
    """
        Schema for password set
    """
    pwd = colander.SchemaNode(
        colander.String(),
        validator=colander.Length(min=4),
        widget=widget.CheckedPasswordWidget(size=20),
        title=u"",
        missing=deferred_missing_password)


class UserFormSchema(colander.MappingSchema):
    """
        Schema for user add
    """
    user = AccountSchema(title=u"Utilisateur")
    companies = CompanySchema(
        title=u"Entreprise(s)",
        widget=widget.SequenceWidget(
            add_subitem_text_template=u"Ajouter une entreprise")
    )
    password = Password(title=u"Mot de passe")


class AuthSchema(colander.MappingSchema):
    """
        Schema for authentication form
    """
    login = colander.SchemaNode(
        colander.String(),
        title="Identifiant")
    password = colander.SchemaNode(
        colander.String(),
        widget=widget.PasswordWidget(),
        title="Mot de passe")
    nextpage = colander.SchemaNode(
        colander.String(),
        widget=widget.HiddenWidget()
    )


def get_auth_schema():
    """
        return the authentication form schema
    """
    return AuthSchema(title=u"Authentification", validator=auth)


def get_user_schema(request, edit):
    """
        Return the user schema
        user:the avatar of the user in the current session
    """
    schema = UserFormSchema().clone()
    user = request.user
    if user.is_admin():
        companies = get_companies_choices()
        return schema.bind(edit=edit, companies=companies)

    elif user.is_manager():
        companies = get_companies_choices()
        # manager can't set admin rights
        roles = MANAGER_ROLES
        group = schema['user']['primary_group']
        group.validator = colander.OneOf([x[0] for x in roles])
        group.widget = widget.RadioChoiceWidget(values=roles)
        return schema.bind(edit=edit, companies=companies)

    else:
        # Non admin users are limited
        del schema['user']['code_compta']
        del schema['user']['primary_group']
        del schema['companies']
        del schema['password']
        return schema.bind(edit=True)


def get_password_change_schema():
    """
        Return the password changing schema
    """
    return PasswordChangeSchema(
        validator=auth,
        title=u'Modification de mot de passe')


class DeleteUserSchema(colander.MappingSchema):
    disable = colander.SchemaNode(
        colander.Boolean(),
        default=True,
        title=u"Désactiver cet utilisateur",
        description=u"""Désactiver un utilisateur l'empêche de se
connecter mais permet de conserver l'intégralité
des informations concernant son activité.""")
    companies = colander.SchemaNode(
        colander.Boolean(),
        title=u"Désactiver ses entreprises",
        description=u"Entraîne automatiquement la désactivation des employés.",
        default=True)


def get_user_del_schema(user):
    """
        Return the user delete form schema
    """
    schema = DeleteUserSchema().clone()
    for companies in user.companies:
        if len(companies.employees) > 1:
            schema['companies'].default = False
            schema['companies'].description += u"Attention : Au moins l'une \
            de ses entreprises a plusieurs employés"
            break
    return schema
