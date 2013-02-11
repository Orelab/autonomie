# -*- coding: utf-8 -*-
# * File Name : __init__.py
#
# * Copyright (C) 2012 Majerti <tech@majerti.fr>
#   This software is distributed under GPLV3
#   License: http://www.gnu.org/licenses/gpl-3.0.txt
#
# * Creation Date : 11-01-2012
# * Last Modified : lun. 11 févr. 2013 15:35:06 CET
#
# * Project : autonomie
#
"""
    Main file for our pyramid application
"""
import locale
from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from pyramid_beaker import set_cache_regions_from_settings
from sqlalchemy import engine_from_config

from pyramid.authentication import SessionAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

from autonomie.utils.security import RootFactory
from autonomie.utils.security import BaseDBFactory
from autonomie.utils.security import wrap_db_objects

from autonomie.models.initialize import initialize_sql
from autonomie.models.config import get_config
from autonomie.utils.avatar import get_groups
from autonomie.utils.avatar import get_avatar
from autonomie.utils.renderer import set_deform_renderer
from autonomie.utils.renderer import set_json_renderer
from autonomie.utils.session import get_session_factory
from autonomie.utils.deform_bootstrap_fix import add_resources_to_registry


AUTONOMIE_MODULES = (
                     "autonomie.views.static",
                     "autonomie.views.auth",
                     "autonomie.views.user",
                     "autonomie.views.company",
                     "autonomie.views.index",
                     "autonomie.views.client",
                     "autonomie.views.project",
                     "autonomie.views.company_invoice",
                     "autonomie.views.admin",
                     "autonomie.views.manage",
                     "autonomie.views.holiday",
                     "autonomie.views.tests",
                     "autonomie.views.estimation",
                     "autonomie.views.invoice",
                     "autonomie.views.cancelinvoice",
                     "autonomie.views.json",
                     "autonomie.views.subscribers",
                     "autonomie.views.commercial",
                     )


def main(global_config, **settings):
    """
        Main function : returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    session_factory = get_session_factory(settings)
    set_cache_regions_from_settings(settings)
    auth_policy = SessionAuthenticationPolicy(callback=get_groups)
    acl_policy = ACLAuthorizationPolicy()

    config = Configurator(settings=settings,
                        authentication_policy=auth_policy,
                        authorization_policy=acl_policy,
                        session_factory=session_factory)
    config.begin()
    config.commit()

    dbsession = initialize_sql(engine)
    wrap_db_objects()
    BaseDBFactory.dbsession = dbsession
    config._set_root_factory(RootFactory)

    # Application main configuration
    config.set_default_permission('view')

    # Adding some properties to the request object
    config.set_request_property(lambda _: dbsession(), 'dbsession', reify=True)
    config.set_request_property(get_avatar, 'user', reify=True)
    config.set_request_property(lambda _:get_config(), 'config')

    statics = settings.get('autonomie.statics', 'static')
    config.add_static_view(statics, "autonomie:static", cache_max_age=3600)
    config.add_static_view(statics + "-deform",
            "deform:static",
            cache_max_age=3600)
    config.add_static_view(statics + "-deform_bootstrap",
            "deform_bootstrap:static",
            cache_max_age=3600)

    # Adding a static view to the configured assets
    assets = settings.get('autonomie.assets', '/var/intranet_files')
    config.add_static_view('assets', assets, cache_max_age=3600)


    for module in AUTONOMIE_MODULES:
        config.include(module)
    # * Treasury
    config.add_route('company_treasury',
                     '/company/{id:\d+}/treasury',
                     traverse='/companies/{id}')

    # Set deform multi renderer handling translation and both chameleon and
    # mako templates
    set_deform_renderer()
    set_json_renderer(config)
    config.add_translation_dirs("colander:locale/", "deform:locale")
    locale.setlocale(locale.LC_ALL, "fr_FR.UTF-8")
    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
    add_resources_to_registry()

    return config.make_wsgi_app()


def formalchemy(config):
    config.include("autonomie.fainit")
    config.include("autonomie.faroutes")
