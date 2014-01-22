#! /usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2013 Fondazione Bruno Kessler
#  Author: <consonni@fbk.eu>
#  This work has been funded by Fondazione Bruano Kessler (Trento, Italy)
#  under projects T2DataExchange and LOD4STAT
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

import ogr
import osr

NODE_TYPES = (ogr.wkbPoint, )
WAY_TYPES = (ogr.wkbLineString, ogr.wkbPolygon)
RELATION_TYPES = (ogr.wkbMultiPoint,
                  ogr.wkbMultiLineString,
                  ogr.wkbGeometryCollection
                  )


def MBR(geom):
    points = geom.GetPoints()
    if points:
        return {'min': {'lon': min([p[0] for p in points]),
                        'lat': min([p[1] for p in points])
                        },
                'max': {'lon': max([p[0] for p in points]),
                        'lat': max([p[1] for p in points])
                        }
                }


def get_boundpoints(mbr):
    minpoint = ogr.Geometry(ogr.wkbPoint)
    minpoint.AddPoint(mbr['min']['lon'], mbr['min']['lat'])
    maxpoint = ogr.Geometry(ogr.wkbPoint)
    maxpoint.AddPoint(mbr['max']['lon'], mbr['max']['lat'])
    return minpoint, maxpoint


def distance_reproject(minpoint, maxpoint, sourceSR):
    targetSR = osr.SpatialReference()
    targetSR.ImportFromEPSG(23032)
    coordTrans = osr.CoordinateTransformation(sourceSR, targetSR)
    minpoint.Transform(coordTrans)
    maxpoint.Transform(coordTrans)
    return minpoint.Distance(maxpoint)


def main():
    ds = ogr.Open("data/OSM/Wikipedia-data-in-OSM.osm")

    osmObjs = dict()

    i = 0
    layers = []
    while ds.GetLayerByIndex(i) is not None:
        layers.append(ds.GetLayerByIndex(i))
        i = i + 1

    for lyr in layers:
        for feat in lyr:
            geom = feat.geometry()
            geom_type = geom.GetGeometryType()

            if geom_type in NODE_TYPES:
                continue
            if geom_type in WAY_TYPES:
                osm_type = 'w'
            elif geom_type in RELATION_TYPES:
                osm_type = 'r'
                continue
            else:
                print 'Error: unknown OSM type'
                continue

            osm_id = feat['osm_id']

            centroid = geom.Centroid()
            x = centroid.GetX()
            y = centroid.GetY()

            osm_obj = osm_type + str(osm_id)

            osmObjs[osm_obj] = {'coords': [], 'dim': 0}
            osmObjs[osm_obj]['coords'] = [x, y]

            print osm_obj

            mbr = None
            if geom_type in WAY_TYPES or geom_type in RELATION_TYPES:
                mbr = MBR(geom)
                if mbr:
                    minpoint, maxpoint = get_boundpoints(mbr)

                    sourceSR = lyr.GetSpatialRef()
                    dist = distance_reproject(minpoint, maxpoint, sourceSR)
                    osmObjs[osm_obj]['dim'] = dist
                else:
                    continue

    return osmObjs


if __name__ == '__main__':
    osmObjs = main()
    import pdb
    pdb.set_trace()
