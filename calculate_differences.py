#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2014 - Fondazione Bruno Kessler.
#  Autore: Cristian Consonni <consonni@fbk.eu>
#
#  This file is part of wikipedia-tags-in-osm.
#  wikipedia-tags-in-osm is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or (at your
#  option) any later version.
#
#  wikipedia-tags-in-osm is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with wikipedia-tags-in-osm.
#  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
sys.path.append('/home/cristian/.virtualenvs/wtosm/lib/python2.7/site-packages')
from geopy.distance import vincenty

import math
from unicodecsv import UnicodeWriter
from query_utils import query_wrapper


SPLIT_RATIO = 0.6


def _query_wrapper_factory(app):
    def _query_wrapper(query):
        return query_wrapper(app.wOSMdb, query, app.libspatialitePath)

    return _query_wrapper


def _get_threshold(alist, split_ratio=0.5):
    """ Gives the value of the element in a list of numbers for which a
    fraction of split_value elements are in the lower part of the list.
    If split_value is 0.5 then return the median"""

    # returns a sorted copy
    srtd = sorted(alist)

    # split_values is expected to be among 0 and 1
    assert(split_ratio >= 0. and split_ratio <= 1.)

    # remember that integer division truncates
    split_element_index = int(math.floor(len(alist)*split_ratio))

    return srtd[split_element_index] if srtd else 0


def _test_intersection_factory(app, _type):
    # instantiate query wrapper
    _query_wrapper = _query_wrapper_factory(app)

    def _test_intersection(wkt, osm_id):

        isWithinConcaveHull = False
        isWithinConvexHull = False

        assert(_type == 'relations' or _type == 'ways' )

        if _type == 'ways':
            id_name = 'way_id'
        elif _type == 'relations':
            id_name = 'rel_id'
        else:
            raise ValueError(u"type should be 'ways' or 'relations', got"
                             "'{0}'' instead".format(_type)
                             )

        query = """SELECT PtDistWithin(
                       ST_GeomFromText('{wkt}'),
                       concave_hull,
                       0
                    )
                    FROM osm_{_type}_centroids
                    WHERE {id_name}={_id}
                 """.format(_type=_type,
                            wkt=wkt,
                            id_name=id_name,
                            _id=osm_id[1:]
                            )

        result = _query_wrapper(query).fetchall()
        isWithinConcaveHull = True \
            if result and result[0][0] else False

        if not isWithinConcaveHull:
            query = """SELECT PtDistWithin(
                           ST_GeomFromText('{wkt}'),
                           convex_hull,
                           0
                        )
                        FROM osm_{_type}_centroids
                        WHERE {id_name}={_id}
                     """.format(_type=_type,
                                wkt=wkt,
                                id_name=id_name,
                                _id=osm_id[1:]
                                )
            result = _query_wrapper(query).fetchall()

            isWithinConvexHull = True \
                if result and result[0][0] else False

        return isWithinConcaveHull, isWithinConvexHull

    return _test_intersection


def calculate(app):
    _intersection_relations = _test_intersection_factory(app, 'relations')
    _intersection_ways = _test_intersection_factory(app, 'ways')

    query = "SELECT count(*) FROM osm_ways_centroids"
    waysOK = True if _query_wrapper_factory(app)(query).fetchone() \
        else False

    query = "SELECT count(*) FROM osm_relations_centroids"
    relationsOK = True if _query_wrapper_factory(app)(query).fetchone() \
        else False

    count0 = 0
    count1 = 0
    count2 = 0
    count_none = 0
    count_total = 0
    for theme in app.themes:
        for category in theme.categories:
            category_distances_nodes = []
            category_distances_ways = []
            category_distances_relations = []

            category.threshold_distance = 0

            for article in category.allArticles:
                article.distance = None
                if app.titlesCoords.get(article.name, None):
                    if hasattr(article, 'osmIds') and article.osmIds:

                        # sort OSM object based on type: node first, then way
                        # then relation
                        alphabet = 'nwr'
                        osm_ids = sorted(
                            article.osmIds,
                            key=lambda osm_id: alphabet.index(osm_id[0]))

                        wlat = article.wikipediaCoords[0]
                        wlon = article.wikipediaCoords[1]
                        wkt = 'POINT({lon} {lat})'.format(lon=wlon,
                                                          lat=wlat
                                                          )

                        article.distance = {}
                        article.diffStatus = {}

                        for osm_id in osm_ids:
                            # calculate vicenty distance between Wikipedia
                            # coords and centroid
                            article.distance[osm_id] = vincenty(
                                article.OSMcoords,
                                article.wikipediaCoords).meters

                            if osm_id[0] == 'n':
                                # object is a node
                                # create list of distances for nodes
                                # to compute the threshold after
                                category_distances_nodes.append(
                                    article.distance[osm_id])

                            elif osm_id[0] == 'w':
                                # object is a way
                                # create list of distances for nodes
                                # to compute the threshold after
                                category_distances_ways.append(
                                    article.distance[osm_id])

                                article.diffStatus[osm_id] = 0
                                if waysOK:
                                    isWithinConcaveHull, isWithinConvexHull = \
                                        _intersection_ways(wkt, osm_id)

                                    if isWithinConcaveHull:
                                        article.diffStatus[osm_id] = 2
                                    elif isWithinConvexHull:
                                        article.diffStatus[osm_id] = 1
                                    else:
                                        article.diffStatus[osm_id] = 0

                            else:
                                # object is a relation
                                # create list of distances for nodes
                                # to compute the threshold after
                                category_distances_relations.append(
                                    article.distance[osm_id])

                                article.diffStatus[osm_id] = 0
                                if relationsOK:
                                    isWithinConcaveHull, isWithinConvexHull = \
                                        _intersection_relations(wkt, osm_id)

                                    if isWithinConcaveHull:
                                        article.diffStatus[osm_id] = 2
                                    elif isWithinConvexHull:
                                        article.diffStatus[osm_id] = 1
                                    else:
                                        article.diffStatus[osm_id] = 0

            category.threshold_distance_nodes_lower = _get_threshold(
                category_distances_nodes,
                SPLIT_RATIO)

            category.threshold_distance_nodes_upper = _get_threshold(
                category_distances_nodes,
                SPLIT_RATIO/2)

            category.threshold_distance_ways = _get_threshold(
                category_distances_ways,
                SPLIT_RATIO)

            category.threshold_distance_relations = _get_threshold(
                category_distances_relations,
                SPLIT_RATIO)

            # print u"  - Threshold value for category {0}:".format(
            #     category.name)
            # print u"      * nodes: upper: {0} - lower: {1}".format(
            #     category.threshold_distance_nodes_upper,
            #     category.threshold_distance_nodes_lower)
            # print u"      * ways: {0}".format(
            #     category.threshold_distance_ways)
            # print u"      * relations: {0}".format(
            #     category.threshold_distance_relations)

            for article in category.allArticles:
                score = 0
                if article.distance:
                    for osm_id in article.osmIds:
                        centroid_distance = article.distance[osm_id]

                        if osm_id[0] == 'n':
                            tier1 = category.threshold_distance_nodes_upper
                            tier2 = category.threshold_distance_nodes_lower

                            if centroid_distance <= tier1:
                                article.diffStatus[osm_id] = 2
                            elif centroid_distance <= tier2:
                                article.diffStatus[osm_id] = 1
                            else:
                                article.diffStatus[osm_id] = 0

                        elif osm_id[0] == 'w':
                            if article.diffStatus[osm_id] == 1 and \
                                    centroid_distance > \
                                    category.threshold_distance_ways:
                                article.diffStatus[osm_id] == 0

                        else:
                            if article.diffStatus[osm_id] == 1 and \
                                    centroid_distance > \
                                    category.threshold_distance_relations:
                                article.diffStatus[osm_id] == 0

                    for osm_id in article.osmIds:
                        score = score + article.diffStatus[osm_id]

                    score = round(score/float(len(article.osmIds)), 0)

                    article.diffStatusOK = score

                    if article.diffStatusOK == 0:
                        count0 = count0 + 1
                    elif article.diffStatusOK == 1:
                        count1 = count1 + 1
                    else:
                        count2 = count2 + 1

                else:
                    count_none = count_none + 1
                    article.diffStatusOK = None

            count_total = count_total + len(category.allArticles)

    print """* Statistics about distance calculation
  ** class 0: {0}
  ** class 1: {1}
  ** class 2: {2}
  ** no distance: {3}
  TOTAL: {4}
""".format(count0, count1, count2, count_none, count_total)


def save(app):

    outfile = os.path.join('data', 'differences', 'distance.csv')

    with open(outfile, 'w+') as out:
        outcsv = UnicodeWriter(out)

        for theme in app.themes:
            for category in theme.categories:
                for article in category.allArticles:
                    if article.distance is not None:
                        outcsv.writerow([article.name,
                                         article.osmIds[0],
                                         str(article.distance)
                                         ])


if __name__ == '__main__':
    print 'Hello, world!'
