<%doc>
 * Copyright (C) 2012-2014 Croissance Commune
 * Authors:
       * Arezki Feth <f.a@majerti.fr>;
       * Miotte Julien <j.m@majerti.fr>;
       * TJEBBES Gaston <g.t@majerti.fr>

 This file is part of Autonomie : Progiciel de gestion de CAE.

    Autonomie is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Autonomie is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Autonomie.  If not, see <http://www.gnu.org/licenses/>.
</%doc>
<%doc>
    User datas edition page
    Include two forms, one for datas edition, the other for doctypes
    registration
</%doc>
<%inherit file="/base.mako"></%inherit>
<%namespace file="/base/utils.mako" import="table_btn"/>
<%namespace file="/base/utils.mako" import="format_filelist" />
<%block name="content">
<% userdata = request.context %>
<div class='well'>
% if userdata.__name__ == 'userdatas':
    % if getattr(userdata, "user_id", None) is not None:
        Ces données sont associées à un compte utilisateur : <a href='${request.route_path("user", id=userdata.user_id)}'>Voir</a>
    % endif
    <% del_url = request.route_path('userdata', id=userdata.id, _query=dict(action="delete")) %>
    <% del_msg = u'Êtes vous sûr de vouloir supprimer les données de cette personne ?' %>
    % if userdata.user is not None:
        <% del_msg += u" Le compte associé sera également supprimé. Cette action n\\'est pas réversible." %>
    % endif
    <a class='btn btn-danger pull-right' href="${del_url}" title="Supprimer ces données" onclick="return confirm('${del_msg}');">
        <i class="glyphicon glyphicon-white icon-trash"></i>
        Supprimer les données
    </a>
% endif
</div>
<% user = getattr(request.context, "user", None) %>

<ul class='nav nav-tabs' role="tablist">
    <li class='active'>
        <a href="#tab1" data-toggle='tab' aria-expanded="false" aria-controls="home" role="tab">
            Informations sociales
        </a>
    </li>
    % if doctemplates is not UNDEFINED:
    <li>
        <a href="#tab4" data-toggle='tab'>
            Génération de documents
        </a>
        </li>
    % endif
    % if doctypes_form is not UNDEFINED:
        <li>
        <a href="#tab2" data-toggle='tab'>
            Documents sociaux
        </a>
        </li>
    % endif
    % if account_form is not UNDEFINED and account_form is not None:
        <li>
        <a href="#tab3" data-toggle='tab'>
            Compte utilisateur
            % if user is not None and not user.enabled():
                <span class='label label-warning'>Ce compte a été désactivé</span>
            % endif
        </a>
        </li>
    % endif
    % if user is not None:
        <li>
        <a href="#tab5" data-toggle='tab'>
            Entreprise(s)
        </a>
        </li>
    % endif
</ul>
<div class='tab-content'>
    <div class='tab-pane row active' id='tab1'>
        ${form|n}
    </div>
    % if doctypes_form is not UNDEFINED:
    <div class='tab-pane row' id='tab2'>
        <div class='col-md-8'>
            ${doctypes_form.render()|n}
        </div>
        <div class='col-md-4'>
            <h3>Liste des documents déposés dans Autonomie</h3>
            <a class='btn btn-success'
                href="${request.route_path('userdata', id=userdata.id, _query=dict(action='attach_file'))}"
                title="Déposer un document scanné dans autonomie">
                Déposer un document
            </a>
            ${format_filelist(userdata)}
        </div>
    </div>
    % endif
    % if account_form is not UNDEFINED and account_form is not None:
        <div class='tab-pane row' id='tab3'>
            ${account_form.render()|n}
        </div>
    % endif
    % if doctemplates is not UNDEFINED:
    <div class='tab-pane row' id='tab4'>
        <div class='row'>
            <div class='col-md-6'>
        % for doctemplate in doctemplates:
            <% url = request.route_path('userdata', id=userdata.id, _query=dict(template_id=doctemplate.id, action="py3o")) %>
            <a class='btn btn-success' href="${url}">
                <i class="fa fa-file fa-1x"></i>
                ${doctemplate.description} ( ${doctemplate.name} )
            </a>
        % endfor
        % if doctemplates == []:
            <div class='well'>
            <i class='fa fa-question-circle fa-2x'></i>
            Vous devez déposer des modèles de document dans Autonomie pour pouvoir accéder à cet outil.
                <br />
            % if request.user.is_admin():
                <a href="${request.route_path('templates')}">Déposer de nouveau modèle de document</a>
            % else:
                Veuillez vous addresser à un administrateur.
            % endif
        </div>
        % endif
            </div>
            <div class='col-md-6'>
                <h3>Historique des documents générés depuis Autonomie</h3>
                <span class='help-block'>
                    <i class='fa fa-question-circle fa-2x'></i>
                    Chaque fois qu'un utilisateur génère un document depuis cette page, une entrée est ajoutée à l'historique.<br />
                    Si nécessaire, pour rendre plus pertinente cette liste, vous pouvez supprimer certains entrées.
                </span>
                <table class='table table-stripped table-condensed'>
                    <thead>
                        <th>Nom du document</th>
                        <th>Généré par</th>
                        <th>Date</th>
                        <th class='text-right'>Actions</th>
                    </thead>
                    <tbody>
                        % for history in userdata.template_history:
                            <tr>
                                <td>${history.template.description}</td>
                                <td>${api.format_account(history.user)}</td>
                                <td>${api.format_datetime(history.created_at)}</td>
                                <td>
                                    <a
                                        class='btn btn-danger'
                                        href="${request.route_path('templatinghistory', id=history.id, _query=dict(action='delete'))}"
                                        ><i class='fa fa-trash fa-1x'></i>
                                        Supprimer cette entrée
                                    </a>
                                </td>
                            </tr>
                        % endfor
                        % if len(userdata.template_history) == 0:
                            <tr><td colspan='4'>Aucun document n'a été généré pour ce compte</td></tr>
                        % endif
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    % endif
    % if user is not None:
        <div class='tab-pane row' id='tab5'>
            <a href="${request.route_path('companies', _query=dict(action='add', user_id=user.id))}" class='btn btn-success'>
                Associer à une nouvelle entreprise
            </a>
            <a href="${request.route_path('userdata', id=userdata.id, _query=dict(action='associate'))}" class='btn btn-success'>
                Associer à une entreprise existante
            </a>
            <table class="table table-striped table-condensed table-hover">
                <thead>
                    <th>Nom</th>
                    <th>Adresse e-mail</th>
                    <th>Entrepreneur(s)</th>
                    <th style="text-align:center">Actions</th>
                </thead>
                <tbody>
                    % for company in user.companies:
                        <% url = request.route_path('company', id=company.id, _query=dict(action='edit')) %>
                        <% onclick = "document.location='{url}'".format(url=url) %>
                        <tr>
                            <td onclick="${onclick}" class="rowlink">
                                ${company.name}
                                % if not company.enabled():
                                    <span class='label label-warning'>Cette entreprise a été désactivée</span>
                                % endif
                            </td>
                            <td onclick="${onclick}" class="rowlink">
                                ${company.email}
                            </td>
                            <td onclick="${onclick}" class="rowlink">
                                <ul>
                                    % for user in company.employees:
                                        <li>
                                            <a href="${request.route_path('user', id=user.id)}">
                                                ${api.format_account(user)}
                                            </a>
                                        </li>
                                    % endfor
                                </ul>
                            </td>
                            <td>
                                ${table_btn(url, u"Modifier", u"Modifier l'entreprise", icon='glyphicon glyphicon-pencil')}
                                % if company.enabled():
                                    <% url = request.route_path('company', id=company.id, _query=dict(action="disable")) %>
                                    ${table_btn(url, u"Désactiver", u"désactiver l'entreprise", icon='glyphicon glyphicon-pencil')}
                                % else:
                                    <% url = request.route_path('company', id=company.id, _query=dict(action="enable")) %>
                                    ${table_btn(url, u"Activer", u"Activer l'entreprise", icon='glyphicon glyphicon-pencil')}
                                % endif
                            </td>
                        </tr>
                    % endfor
                </tbody>
            </table>
        </div>
    % endif
</div>
</%block>
