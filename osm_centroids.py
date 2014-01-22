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


import argparse
import ogr
import osr
import os


class OSMcentroids(object):

    def __init__(self, wOSMFile, wOSMdb, args=None):
        self.wOSMFile = wOSMFile
        self.wOSMdb = wOSMdb
        self.args = args

        self.use_spatialite = False
        try:
            import pyspatialite
            from pyspatialite import dbapi2 as spatialite
            from subprocess import Popen, PIPE, call
            self.use_spatialite = True
        except ImportError as e:
            print e
            self.use_spatialite = False

        if self.use_spatialite:
            self = OSMcentroidsSpatialite(wOSMFile=self.wOSMFile,
                                          wOSMdb=self.wOSMdb,
                                          args=self.args)
        else:
            import ogr
            self = OSMcentroidsOGR(wOSMFile=self.wOSMFile,
                                   wOSMdb=self.wOSMdb,
                                   args=self.args)


class OSMcentroidsOGR(object):
    NODE_TYPES = (ogr.wkbPoint, )
    WAY_TYPES = (ogr.wkbLineString, ogr.wkbPolygon)
    RELATION_TYPES = (ogr.wkbMultiPoint,
                      ogr.wkbMultiLineString,
                      ogr.wkbGeometryCollection
                      )

    def __init__(self, wOSMFile, wOSMdb, args=None):
        self.wOSMFile = wOSMFile
        self.wOSMdb = wOSMdb
        self.args = args
        self.use_spatialite = True

        self.relations_centroids = dict()
        self.ways_centroids = dict()

    @staticmethod
    def _MBR(geom):
        points = geom.GetPoints()
        if points:
            return {'min': {'lon': min([p[0] for p in points]),
                            'lat': min([p[1] for p in points])
                            },
                    'max': {'lon': max([p[0] for p in points]),
                            'lat': max([p[1] for p in points])
                            }
                    }

    @staticmethod
    def _get_boundpoints(mbr):
        minpoint = ogr.Geometry(ogr.wkbPoint)
        minpoint.AddPoint(mbr['min']['lon'], mbr['min']['lat'])
        maxpoint = ogr.Geometry(ogr.wkbPoint)
        maxpoint.AddPoint(mbr['max']['lon'], mbr['max']['lat'])
        return minpoint, maxpoint

    @staticmethod
    def _distance_reproject(minpoint, maxpoint, sourceSR):
        targetSR = osr.SpatialReference()
        targetSR.ImportFromEPSG(23032)
        coordTrans = osr.CoordinateTransformation(sourceSR, targetSR)
        minpoint.Transform(coordTrans)
        maxpoint.Transform(coordTrans)
        return minpoint.Distance(maxpoint)

    def import_data(self):
        self.ds = ogr.Open(self.wOSMFile)
        return self.ds

    def 
        i = 0
        layers = []
        while self.ds.GetLayerByIndex(i) is not None:
            layers.append(self.ds.GetLayerByIndex(i))
            i = i + 1

        for lyr in layers:

            count_feats = 0
            for feat in lyr:

                count_feats = count_feats + 1

                geom = feat.geometry()
                geom_type = geom.GetGeometryType()

                if geom_type in self.NODE_TYPES:
                    continue
                if geom_type in self.WAY_TYPES:
                    osm_type = 'w'
                elif geom_type in self.RELATION_TYPES:
                    osm_type = 'r'
                else:
                    print 'Error: unknown OSM type'
                    import pdb
                    pdb.set_trace()

                osm_id = feat['osm_id']

                centroid = geom.Centroid()
                x = centroid.GetX()
                y = centroid.GetY()

                print osm_type + str(osm_id)

                if geom_type in WAY_TYPES or geom_type in RELATION_TYPES:
                    mbr = MBR(geom)
                    minpoint, maxpoint = get_boundpoints(mbr)

                    sourceSR = lyr.GetSpatialRef()
                    dist = distance_reproject(minpoint, maxpoint, sourceSR)

    def drop_database(self):
        pass


class OSMcentroidsSpatialite(object):

    def __init__(self, wOSMFile, wOSMdb, args=None):
        self.wOSMFile = wOSMFile
        self.wOSMdb = wOSMdb
        self.args = args
        self.use_spatialite = True

        if self.args is not None:

            if self.args.drop_database:
                self.drop_database()

            elif self.args.drop_ways_centroids_table:
                self.drop_table('osm_ways_centroids')

            elif self.args.drop_relations_centroids_table:
                self.drop_table('osm_relations_centroids')

            else:
                if self.args.import_data:
                    self.import_data()

                if self.args.ways:
                    self.create_ways_centroids()

                if self.args.relations:
                    self.create_relations_centroids()

                if self.args.update_ways:
                    self.update_ways_with_dims()

                if self.args.update_relations:
                    self.update_relations_with_dims()

    def import_data(self):
        """Import OSM data with Wikipedia tag in a sqlite database to calculate
           centroids
        """

        print "Import dei dati dal file OSM: "
        print self.wOSMFile
        print "nel database Spatialite: "
        print self.wOSMdb
        print

        command = "spatialite_osm_raw -o {wosm_file} -d {wtosm_db}".format(
            wosm_file=self.wOSMFile,
            wtosm_db=self.wOSMdb)
        call(command, shell=True)

        print
        print "Import completato!"

    def _query_wrapper(self, query):
        con = spatialite.connect(self.wOSMdb)

        try:
            with con:
                cur = con.cursor()
            cur.execute(query)
        except spatialite.OperationalError as error:
            print "Failed execution of query:\n%s" % query
            print error
            print "Nessuna tabella creata"

        return cur

    def update_ways_with_dims(self):
        query = """UPDATE osm_ways_centroids
                   SET dist = GeodesicLength(
                                MakeLine(
                                    PointFromText(p1,4326),
                                    PointFromText(p2,4326)
                                    )
                                )
                """

        print 'Executing: ', query

        self._query_wrapper(query)

    def create_ways_centroids(self):
        query = """CREATE TABLE osm_ways_centroids
                   AS SELECT way_id,
                             AsText(Centroid(ST_Collect(Geometry))) as centr,
                             AsText(
                                MakePoint(MbrMinX(ST_Collect(Geometry)),
                                          MbrMinY(ST_Collect(Geometry)),
                                          4326
                                          )
                                ) as p1,
                             AsText(
                                 MakePoint(MbrMaxX(ST_Collect(Geometry)),
                                           MbrMaxY(ST_Collect(Geometry)),
                                           4326
                                           )
                                 ) as p2,
                             GeodesicLength(
                                 MakeLine(
                                     MakePoint(MbrMinX(ST_Collect(Geometry)),
                                               MbrMinY(ST_Collect(Geometry)),
                                               4326
                                               ),
                                     MakePoint(MbrMaxX(ST_Collect(Geometry)),
                                               MbrMaxY(ST_Collect(Geometry)),
                                               4326
                                               )
                                     )
                                 ) as dist
                      FROM osm_way_refs AS w
                      JOIN osm_nodes AS n
                      ON w.node_id = n.node_id
                      GROUP BY way_id
                """

        self._query_wrapper(query)

        con = spatialite.connect(self.wOSMdb)

        query = """SELECT Count(*)
                   FROM osm_ways_centroids
                """

        try:
            with con:
                cur = con.cursor()
            cur.execute(query)
            num = cur.fetchone()[0]
            print "Creata una tabella con %d righe" % num
        except spatialite.OperationalError as error:
            print "Failed execution of query:\n%s" % query
            print error

    def update_relations_with_dims(self):
        query = """UPDATE osm_relations_centroids
                   SET dist = GeodesicLength(
                                MakeLine(
                                    PointFromText(p1,4326),
                                    PointFromText(p2,4326)
                                    )
                                )
                    WHERE dist is NULL
                """

        self._query_wrapper(query)

    def create_relations_centroids(self):
        con = spatialite.connect(self.wOSMdb)

        query = """CREATE TABLE osm_relations_centroids_source
                   AS SELECT rel_id, type, ref, Geometry
                   FROM osm_relation_refs AS rr
                   JOIN (SELECT way_id, w.node_id, Geometry
                         FROM osm_way_refs AS w
                         JOIN osm_nodes AS n
                         ON w.node_id = n.node_id
                         ) AS nw
                   ON (type = "W" AND rr.ref = nw.way_id)
                """

        self._query_wrapper(query)

        query = """INSERT INTO osm_relations_centroids_source
                   SELECT rel_id, type, ref, Geometry
                   FROM osm_relation_refs AS rr
                   JOIN osm_nodes AS n
                   ON (type = "N" AND rr.ref = n.node_id)
                """
        self._query_wrapper(query)

        query = """CREATE TABLE osm_relations_centroids
                   AS SELECT rel_id,
                             AsText(Centroid(ST_Collect(Geometry))) as centr,
                             AsText(
                                MakePoint(MbrMinX(ST_Collect(Geometry)),
                                          MbrMinY(ST_Collect(Geometry)),
                                          4326
                                          )
                                ) as p1,
                             AsText(
                                 MakePoint(MbrMaxX(ST_Collect(Geometry)),
                                           MbrMaxY(ST_Collect(Geometry)),
                                           4326
                                           )
                                 ) as p2,
                             GeodesicLength(
                                 MakeLine(
                                     MakePoint(MbrMinX(ST_Collect(Geometry)),
                                               MbrMinY(ST_Collect(Geometry)),
                                               4326
                                               ),
                                     MakePoint(MbrMaxX(ST_Collect(Geometry)),
                                               MbrMaxY(ST_Collect(Geometry)),
                                               4326
                                               )
                                     )
                                 ) as dist
                   FROM osm_relations_centroids_source
                   GROUP BY rel_id
                """
        self._query_wrapper(query)

        self.update_relations_with_dims()

        query = """SELECT Count(*)
                   FROM osm_relations_centroids
                """

        try:
            with con:
                cur = con.cursor()
            cur.execute(query)
            num = cur.fetchone()[0]
            print "Creata una tabella con %d righe" % num
        except spatialite.OperationalError as error:
            print "Failed execution of query:\n%s" % query
            print error
            print "Nessuna tabella creata"
        finally:
            with con:
                cur = con.cursor()
            cur.execute("DROP TABLE osm_relations_centroids_source")
            print "Drop TEMP table osm_relations_centroids_source"

    def _get_coords_from_wkt(self, cur):
        centroids = {}
        if cur:
            for obj_id, wkt in cur:
                coords = [float(c)
                          for c in wkt.strip('POINT(').strip(')').split()
                          ]
                coords.reverse()
                centroids[obj_id] = coords

        return centroids

    def get_relations_centroids(self):
        query = """SELECT rel_id, centr
                   FROM osm_relations_centroids
                """

        cur = self._query_wrapper(query)

        return self._get_coords_from_wkt(cur)

    def get_ways_centroids(self):
        query = """SELECT way_id, centr
                   FROM osm_ways_centroids
                """

        cur = self._query_wrapper(query)

        return self._get_coords_from_wkt(cur)

    def _get_dims(self, cur):
        dims = {}
        if cur:
            for obj_id, dist in cur:
                dims[obj_id] = int(round(dist))

        return dims

    def get_relations_dimensions(self):
        query = """SELECT rel_id, dist
                   FROM osm_relations_centroids
                """

        cur = self._query_wrapper(query)

        return self._get_dims(cur)

    def get_ways_dimensions(self):
        query = """SELECT way_id, dist
                   FROM osm_ways_centroids
                """

        cur = self._query_wrapper(query)

        return self._get_dims(cur)

    def drop_table(self, table_name):
        con = spatialite.connect(self.wOSMdb)

        query = "DROP TABLE {}".format(table_name)

        try:
            with con:
                cur = con.cursor()
            cur.execute(query)
        except spatialite.OperationalError as error:
            print "Failed execution of query:\n%s" % query
            print error

    def drop_database(self):
        proc = Popen(["rm", self.wOSMdb], stderr=PIPE)
        status = proc.wait()

        if status == 0:
            print "Rimosso il database {}".format(self.wOSMdb)
        else:
            output = proc.stderr.read()
            print "rm exited with status: {}".format(status)
            print output


def main():
        # Options
        text = 'A partire dal file contenente gli elementi di OSM con il '\
               'tag Wikipedia (creato con osmfilter) ed importa i dati in un '\
               'database SQLite usando Spatialite '\
               '(e in particolare spatialite_osm_raw). '\
               'Quindi crea due tabelle: '\
               '1) osm_ways_centroids '\
               '2) osm_relations_centroids '\
               '- contenenti i centroidi rispettivamente delle way e delle '\
               'relations con un tag Wikipedia.'\
               'Questi dati sono usati nello script principale nella '\
               'creazione delle pagine e in particolare del collegamento a '\
               "Wikipedia per l'inserimento del template {{coord}}"

        parser = argparse.ArgumentParser(description=text)

        parser.add_argument("-d", "--database",
                            help='Nome del database SQLite/Spatialite da '
                                 'creare [default: '
                                 './data/OSM/Wikipedia-data-in-OSM.sqlite]',
                            dest="wOSMdb",
                            default=os.path.join("data",
                                                 "OSM",
                                                 "Wikipedia-data-in-OSM.sqlite"
                                                 ),
                            action="store"
                            )
        parser.add_argument("-f", "--osm_file",
                            help='Nome del file con i dati OSM (creato con '
                                 'osmfilter) [default: '
                                 './data/OSM/Wikipedia-data-in-OSM.osm]',
                            dest="wOSMFile",
                            default=os.path.join("data",
                                                 "OSM",
                                                 "Wikipedia-data-in-OSM.osm"
                                                 ),
                            action="store"
                            )
        parser.add_argument("-i", "--import_data",
                            help="Import data in the Spatialite database",
                            action="store_true"
                            )
        parser.add_argument("-w", "--ways",
                            help="Calculate centroids for ways",
                            action="store_true"
                            )
        parser.add_argument("-r", "--relations",
                            help="Calculate centroids for relations",
                            action="store_true"
                            )
        parser.add_argument("--update-ways-with-dims",
                            help="Update dims for ways",
                            dest="update_ways",
                            action="store_true"
                            )
        parser.add_argument("--update-relations-with-dims",
                            help="Update dims for relations",
                            dest="update_relations",
                            action="store_true"
                            )
        parser.add_argument("--drop_database",
                            help="Elimina il database",
                            action="store_true")
        parser.add_argument("--drop_ways_centroids_table",
                            help='Elimina dal database la tabella con i '
                                 'centroidi delle ways: '
                                 'osm_ways_centroids',
                            action="store_true")
        parser.add_argument("--drop_relations_centroids_table",
                            help='Elimina dal database la tabella con i '
                                 'centroidi delle relations: '
                                 'osm_relations_centroids',
                            action="store_true")

        args = parser.parse_args()
        print args

        print 'Using OSM file: ', args.wOSMFile
        print 'Using Spatialite DB: ', args.wOSMdb

        osm = OSMcentroids(args.wOSMFile, args.wOSMdb, args)

if __name__ == '__main__':
    main()
