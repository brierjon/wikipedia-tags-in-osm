#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2013 Fondazione Bruno Kessler
#  Author: <consonni@fbk.eu>
#  This work has been funded by Fondazione Bruno Kessler (Trento, Italy)
#
#  This file is part of wikipedia-tags-in-osm.
#  wikipedia-tags-in-osm is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  wikipedia-tags-in-osm is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with wikipedia-tags-in-osm.
#  If not, see <http://www.gnu.org/licenses/>.

from pysqlite2 import dbapi2 as spatialite


def query_wrapper(wOSMdb, query, libspatialitePath):
    con = spatialite.connect(wOSMdb)
    con.enable_load_extension(True)
    try:
        with con:
            cur = con.cursor()
        cmd = "SELECT load_extension('%s');" % libspatialitePath
        cur.execute(cmd)
        cur.execute(query)
    except spatialite.OperationalError as error:
        print "Failed execution of query:\n%s" % query
        print error
        print "No table created"

    return cur
