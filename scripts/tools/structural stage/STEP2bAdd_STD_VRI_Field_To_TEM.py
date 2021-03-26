"""

Original Author:
Madrone (Jeff Kruys)

Created on:
2021-02-04

Purpose:
This script overlays a TEM and VRI feature classes and determines the area-dominant VRI_STD
value for each TEM polygon.

Usage:
Add_STD_VRI_Field_To_TEM.py bfc vfc [-h] [-l] [-ld]

Positional Arguments:
   bfc              TEM feature class
   vfc              VRI feature class that contains STD_VRI field
   
Optional Arguments:
  -h, --help       show this help message and exit
  -l, --level      log level messages to display; Default: 20 - INFO
  -ld, --log_dir   path to directory for output log file

Example Input:
X:\fullpath\Add_STD_VRI_Field_To_TEM.py Y:\fullpath\bfc Z:\fullpath\vfc


History
2021-02-04 (JK): Created script.

"""

import logging
import time
import os
import sys
import ctypes
import pdb
import operator

from argparse import ArgumentParser
from argparse import RawTextHelpFormatter

def main(tem_fc, vri_fc):
    logging.info("Initializing...")

    logging.info('Start Time: ' + time.ctime(time.time()))
    dtCalcScriptStart = time.time()

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

        def __init__(self):
            # have to initialize this to the size of MEMORYSTATUSEX
            self.dwLength = ctypes.sizeof(self)
            super(MEMORYSTATUSEX, self).__init__()

    python_script = sys.argv[0]
    script_path = os.path.split(sys.argv[0])[0]

    # ---------------------------------------------------------------------------------------------------------
    #  Function to construct a time string from a number (of seconds)
    # ---------------------------------------------------------------------------------------------------------

    def SanitizeElapsedTime(dtInput):
        if dtInput < 120:
            strElapsedTime = str(int(dtInput)) + ' sec.'
        elif dtInput < 3600:
            strElapsedTime = str(round(dtInput / 60, 1)) + ' min.'
        else:
            strElapsedTime = str(round(dtInput / 3600, 2)) + ' hr.'
        return strElapsedTime

    # ---------------------------------------------------------------------------------------------------------
    # Check that input feature classes exist and contain required fields
    # ---------------------------------------------------------------------------------------------------------

    if not arcpy.Exists(tem_fc):
        logging.error("**** Specified TEM feature class {} does not exist. Exiting script.".format(tem_fc))
        sys.exit()

    teis_id_field_found = False
    for f in arcpy.ListFields(tem_fc):
        if f.name == "TEIS_ID":
            teis_id_field_found = True
            if f.type not in ["Integer", "SmallInteger"]:
                logging.error("**** TEIS_ID field in specified TEM feature class is not a numeric field. "
                              "Exiting script.")
                sys.exit()
    if not teis_id_field_found:
        logging.error("**** Specified TEM feature class does not have a TEIS_ID field. Exiting script.")
        sys.exit()

    if not arcpy.Exists(vri_fc):
        logging.error("**** Specified VRI feature class does not exist. Exiting script.")
        sys.exit()

    existing_vri_fields = [f.name for f in arcpy.ListFields(vri_fc)]
    missing_fields = []
    if "STD_VRI" not in existing_vri_fields:
        logging.error("**** Specified VRI feature class is missing required fields STD_VRI. Exiting script.")
        sys.exit()

    # ---------------------------------------------------------------------------------------------------------
    # Check that TEIS_ID field contains unique values
    # ---------------------------------------------------------------------------------------------------------

    logging.info("Checking that TEM TEIS_ID field contains unique values")
    teis_id_count_dict = {}
    row_count = 0
    total_count = int(arcpy.GetCount_management(tem_fc).getOutput(0))
    dupe_teis_id_found = False
    for row in arcpy.da.SearchCursor(tem_fc, ["TEIS_ID"]):
        row_count += 1
        try:
            teis_id_count_dict[row[0]] += 1
        except:
            teis_id_count_dict[row[0]] = 1
        if teis_id_count_dict[row[0]] > 1:
            dupe_teis_id_found = True
        if row_count % 100000 == 0 or row_count == total_count:
            logging.info("    - Read " + str(row_count) + " of " + str(total_count) + " rows")
    if dupe_teis_id_found:
        logging.info("    - Duplicate TEIS_ID values found. Repopulating TEIS_ID field with OBJECTID values.")
        row_count = 0
        with arcpy.da.UpdateCursor(tem_fc, ["TEIS_ID", "OID@"]) as cursor:
            for row in cursor:
                row_count += 1
                row[0] = row[1]
                cursor.updateRow(row)
                if row_count % 100000 == 0 or row_count == total_count:
                    logging.info("    - Updated " + str(row_count) + " of " + str(total_count) + " rows")
    else:
        logging.info("    - TEIS_ID field contains all unique values.")

    # ---------------------------------------------------------------------------------------------------------
    # Calculate STD_VRI values for each TEM polygon.
    # ---------------------------------------------------------------------------------------------------------

    tab_int_tbl = tem_fc + "_tab_int_vri"
    logging.info("Creating Tabulate Intersection table " + tab_int_tbl)
    if arcpy.Exists(tab_int_tbl):
        arcpy.Delete_management(tab_int_tbl)
    arcpy.TabulateIntersection_analysis(in_zone_features = tem_fc, zone_fields = "TEIS_ID", in_class_features = vri_fc, 
                                        out_table = tab_int_tbl, class_fields = "STD_VRI", sum_fields = "", 
                                        xy_tolerance = "-1 Unknown", out_units = "UNKNOWN")

    row_total = int(arcpy.GetCount_management(tab_int_tbl).getOutput(0))
    tabulate_intersection_succeeded = False

    # We are just going to store the area-dominant age class for STS, and later derive the age class STD from that.
    # Otherwise if we calculate them separately, they may not be "compatible", e.g. age class STS might be 10-20 but
    # age class STD might be 30-50 if they are calculated independently.
    std_vri_dict = {}

    if row_total > 0: ## sometimes the TabulateIntersection tool results in an empty output table for no reason
        logging.info("Reading Tabulate Intersection table to dictionary")
        row_count = 0
        for row in arcpy.da.SearchCursor(tab_int_tbl,["TEIS_ID", "STD_VRI", "AREA"]):
            row_count += 1
            try:
                std_vri_dict[row[0]][row[1]] += row[2]
            except:
                try:
                    std_vri_dict[row[0]][row[1]] = row[2]
                except:
                    std_vri_dict[row[0]] = {}
                    std_vri_dict[row[0]][row[1]] = row[2]
            if row_count % 100000 == 0 or row_count == row_total:
                logging.info("    Read {} of {} rows".format(row_count, row_total))
        tabulate_intersection_succeeded = True

    else: ## if output table was empty, run an Intersect instead
        logging.error("**** Tabulate Intersection output table is empty")
        logging.info("Running an Intersect of TEM and age feature classes")
        intersect_fc = tem_fc + "_int_vri"
        if arcpy.Exists(intersect_fc):
            arcpy.Delete_management(intersect_fc)
        arcpy.Intersect_analysis(in_features = vri_fc + " #;" + tem_fc + " #", out_feature_class = intersect_fc, 
                                 join_attributes = "ALL", cluster_tolerance = "-1 Unknown", output_type = "INPUT")
        row_total = int(arcpy.GetCount_management(intersect_fc).getOutput(0))
        if row_total > 0:
            logging.info("Reading Intersect output feature class table to dictionary")
            row_count = 0
            for row in arcpy.da.SearchCursor(intersect_fc, ["TEIS_ID", "STD_VRI", "SHAPE@AREA"]):
                row_count += 1
                try:
                    std_vri_dict[row[0]][row[1]] += row[2]
                except:
                    try:
                        std_vri_dict[row[0]][row[1]] = row[2]
                    except:
                        std_vri_dict[row[0]] = {}
                        std_vri_dict[row[0]][row[1]] = row[2]
                if row_count % 100000 == 0 or row_count == row_total:
                    logging.info("    Read " + str(row_count) + " of " + str(row_total) + " rows")
        else:
            arcpy.Delete_management(intersect_fc)
            logging.error("Intersection is empty; VRI and PEM/TEM feature classes do not overlap. Exiting.")
            sys.exit()

    tem_fields = [f.name for f in arcpy.ListFields(tem_fc)]
    if "STD_VRI" not in tem_fields:
        logging.info("Adding new field STD_VRI to TEM feature class.")
        arcpy.AddField_management(tem_fc, "STD_VRI", "TEXT", "#", "#", "1")
    else:
        logging.info("Existing values will be overwritten in STD_VRI field in TEM.")

    row_count = 0
    no_std_vri_count = 0
    row_total = int(arcpy.GetCount_management(tem_fc).getOutput(0))
    logging.info("Writing STD_VRI values to TEM")
    with arcpy.da.UpdateCursor(tem_fc,["TEIS_ID", "STD_VRI"]) as cursor:
        for row in cursor:
            row_count += 1
            try:
                biggest_std_vri = max(std_vri_dict[row[0]].iteritems(), key=operator.itemgetter(1))[0]    
                ## see http://stackoverflow.com/questions/268272/getting-key-with-maximum-value-in-dictionary
                row[1] = biggest_std_vri
            except:
                # if the current polygon had no entry in the dictionary, then there is no
                # age class info for the polygon, so assign it values of -1.
                row[1] = ""
                no_std_vri_count += 1
            cursor.updateRow(row)
            if row_count % 100000 == 0 or row_count == row_total:
                logging.info("    Processed {} of {} rows".format(row_count, row_total))
        if no_std_vri_count == 0:
            logging.info("All {} TEM polygon(s) overlapped with an age polygon. That's good!".format(row_total))
        else:
            logging.info("**** WARNING: There were {} polygon(s) for which age classes could "
                         "not be calculated. These polygons probably don't overlap with any polygons in the age "
                         "feature class.".format(no_std_vri_count))
    # arcpy.Delete_management(tab_int_tbl)

    # ---------------------------------------------------------------------------------------------------------
    # Done
    # ---------------------------------------------------------------------------------------------------------

    dtCalcNow = time.time()
    dtCalcScriptElapsed = dtCalcNow - dtCalcScriptStart
    logging.info("Script complete after " + SanitizeElapsedTime(dtCalcScriptElapsed))

if __name__ == '__main__':
    try:
        # Parse arguments
        parser = ArgumentParser(description='This script copies the STD_VRI field from a VRI feature class to a '
                                            'TEM feature class based on area-dominant ',
                                formatter_class=RawTextHelpFormatter)
        parser.add_argument('bfc', help='TEM feature class')
        parser.add_argument('vfc', help='VRI feature class')
        parser.add_argument('-l', '--level', type=int,
                            help='Log level\nValues: 10-DEBUG, 20-INFO(default), 30-WARN, 40-ERROR, 50-CRITICAL')
        parser.add_argument('-ld', '--log_dir', help='Path to log directory')
        args = parser.parse_args()

        # Set up logger
        if args.level is not None and args.level not in [10, 20, 30, 40, 50]:
            raise ValueError('Invalid log level')
        elif args.level is None:
            args.level = 20

        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=args.level)

        # Import arcpy
        import arcpy

        # Start the script
        main(args.bfc, args.vfc)

    except Exception as e:
        logging.exception('Unexpected exception. Program terminating.')
else:
    import arcpy
