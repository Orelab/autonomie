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
    File model
"""

from sqlalchemy import (
        LargeBinary,
        Integer,
        Column,
        ForeignKey,
        String,
        )

from sqlalchemy.orm import (
        deferred,
        )

from sqlalchemy.dialects.mysql.base import LONGBLOB

from autonomie.models.base import default_table_args
from autonomie.models.node import Node


class File(Node):
    """
        A file model
    """
    __tablename__ = 'file'
    __table_args__ = default_table_args
    __mapper_args__ = {'polymorphic_identity': 'file'}
    id = Column(Integer, ForeignKey('node.id'), primary_key=True)
    description = Column(String(100), default="")
    data = deferred(Column(LONGBLOB()))
    mimetype = Column(String(100))
    size = Column(Integer)

    @classmethod
    def from_field_storage(cls, fs):
        """ Create and return an instance of this class from a file upload
            through a webbrowser.

        :param fs: FieldStorage instance as found in a
                   :class:`pyramid.request.Request`'s ``POST`` MultiDict.
        :type fs: :class:`cgi.FieldStorage`

        :result: The created instance.
        :rtype: :class:`kotti.resources.File`
        """

        data = fs.file.read()
        filename = fs.filename
        mimetype = fs.type
        size = len(data)
        return cls(data=data, filename=filename, mimetype=mimetype, size=size)

    def getvalue(self):
        return self.data

    @property
    def label(self):
        return self.description or self.name