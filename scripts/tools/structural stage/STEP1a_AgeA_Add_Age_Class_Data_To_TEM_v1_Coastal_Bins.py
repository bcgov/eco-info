"""

Original Author:
Madrone (Jeff Kruys)

Created on:
2021-01-23

Purpose:
This script takes a feature class that contains Age in years (VRI, etc) and adds the binned ages (classes) to each overlapping polygon in the TEM feature class. 

Usage:
Add_Age_Class_Data_To_tem.py bfc afc afl [-h] [-l] [-ld]

Positional Arguments:
   bfc              tem feature class or table
   afc              Polygon feature class that contains age data
   afl              Name of field that contains age values
   
Optional Arguments:
  -h, --help       show this help message and exit
  -l, --level      log level messages to display; Default: 20 - INFO
  -ld, --log_dir   path to directory for output log file

Example Input:
X:\fullpath\Add_Age_Class_Data_To_tem.py Y:\fullpath\bfc Z:\fullpath\afc age_field_name


History
2021-01-23 (JK): Created script.
2021-02-05 (AE): Changed age_cl_sts bins
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

def main(tem_fc, age_fc, age_field):
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
    #  Function to determine age class (STS) for a given age value in years
    # ---------------------------------------------------------------------------------------------------------

    def calc_age_cl_sts(age_value):
        if age_value >= 0 and age_value <= 2:
            return 2
        elif age_value > 2 and age_value <= 5:
            return 5
        elif age_value > 5 and age_value <= 10:
            return 10
        elif age_value > 10 and age_value <= 20:
            return 20
        elif age_value > 20 and age_value <= 40:
            return 40
        elif age_value > 40 and age_value <= 60:
            return 60
        elif age_value > 60 and age_value <= 80:
            return 80
        elif age_value > 80 and age_value <= 100:
            return 100
        elif age_value > 100 and age_value <= 120:
            return 120
        elif age_value > 120 and age_value <= 140:
            return 140
        elif age_value > 140 and age_value <= 180:
            return 180
        elif age_value > 180 and age_value <= 200:
            return 200
        elif age_value > 200 and age_value <= 250:
            return 250
        elif age_value > 250 and age_value <= 399:
            return 399
        elif age_value > 399:
            return 9999
        else:
            return -1

    # ---------------------------------------------------------------------------------------------------------
    #  Function to determine age class (STD) for a given age class (STS) value in years
    # ---------------------------------------------------------------------------------------------------------

    def calc_age_cl_std(age_cl_sts_value):
        if age_cl_sts_value in [2, 5, 10]:
            return 15
        elif age_cl_sts_value in [20]:
            return 30
        elif age_cl_sts_value in [40]:
            return 50
        elif age_cl_sts_value in [60, 80]:
            return 80
        elif age_cl_sts_value in [100, 120, 140, 180, 200, 250, 399, 9999]:
            return 9999
        else:
            return -1

    # ---------------------------------------------------------------------------------------------------------
    # Check that input feature classes exist and contain required fields
    # ---------------------------------------------------------------------------------------------------------

    if not arcpy.Exists(tem_fc):
        logging.error("**** Specified tem feature class " + tem_fc + " does not exist. Exiting script.")
        sys.exit()
    if not arcpy.Exists(age_fc):
        logging.error("**** Specified age feature class " + age_fc + " does not exist. Exiting script.")
        sys.exit()

    age_field_found = False
    for f in arcpy.ListFields(age_fc):
        if f.name == age_field:
            age_field_found = True
            if f.type not in ["Integer", "SmallInteger", "Single", "Double"]:
                logging.error("**** Specified age field " + age_field + " is type " + str(f.type) + ", not a numeric "
                              "field. Exiting script.")
                sys.exit()
    if not age_field_found:
        logging.error("**** Specified age field " + age_field + " does not exist in specified age feature class. "
                      "Exiting script.")
        sys.exit()

    teis_id_field_found = False
    for f in arcpy.ListFields(tem_fc):
        if f.name == "TEIS_ID":
            teis_id_field_found = True
            if f.type not in ["Integer", "SmallInteger"]:
                logging.error("**** TEIS_ID field in specified tem feature class is not a numeric field. "
                              "Exiting script.")
                sys.exit()
    if not teis_id_field_found:
        logging.error("**** Specified tem feature class does not have a TEIS_ID field. Exiting script.")
        sys.exit()

    # ---------------------------------------------------------------------------------------------------------
    # Check that TEIS_ID field contains unique values
    # ---------------------------------------------------------------------------------------------------------

    logging.info("Checking that tem TEIS_ID field contains unique values")
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
    # Calculate age classes for each polygon. Write them to new fields AGE1_CL_STS and AGE1_CL_STD
    # (or if they exist, AGE2_CL_STS and AGE2_CL_STD, or if they already exist, etc. etc.)
    # ---------------------------------------------------------------------------------------------------------

    tab_int_tbl = os.path.split(tem_fc)[0] + r"\tab_int_tbl"
    logging.info("Creating Tabulate Intersection table " + tab_int_tbl)
    if arcpy.Exists(tab_int_tbl):
        arcpy.Delete_management(tab_int_tbl)
    arcpy.TabulateIntersection_analysis(in_zone_features = tem_fc, zone_fields = "TEIS_ID", in_class_features = age_fc, 
                                        out_table = tab_int_tbl, class_fields = age_field, sum_fields = "", 
                                        xy_tolerance = "-1 Unknown", out_units = "UNKNOWN")

    row_total = int(arcpy.GetCount_management(tab_int_tbl).getOutput(0))
    tabulate_intersection_succeeded = False

    # We are just going to store the area-dominant age class for STS, and later derive the age class STD from that.
    # Otherwise if we calculate them separately, they may not be "compatible", e.g. age class STS might be 10-20 but
    # age class STD might be 30-50 if they are calculated independently.
    age_cl_sts_dict = {}

    if row_total > 0: ## sometimes the TabulateIntersection tool results in an empty output table for no reason
        logging.info("Reading Tabulate Intersection table to dictionary")
        row_count = 0
        for row in arcpy.da.SearchCursor(tab_int_tbl,["TEIS_ID", age_field, "AREA"]):
            row_count += 1
            try:
                age_cl_sts_dict[row[0]][calc_age_cl_sts(row[1])] += row[2]
            except:
                try:
                    age_cl_sts_dict[row[0]][calc_age_cl_sts(row[1])] = row[2]
                except:
                    age_cl_sts_dict[row[0]] = {}
                    age_cl_sts_dict[row[0]][calc_age_cl_sts(row[1])] = row[2]
            if row_count % 100000 == 0 or row_count == row_total:
                logging.info("    Read " + str(row_count) + " of " + str(row_total) + " rows")
        tabulate_intersection_succeeded = True

    else: ## if output table was empty, run an Intersect instead
        logging.error("**** Tabulate Intersection output table is empty")
        logging.info("Running an Intersect of tem and age feature classes")
        intersect_fc = os.path.split(tem_fc)[0] + r"\int_fc"
        if arcpy.Exists(intersect_fc):
            arcpy.Delete_management(intersect_fc)
        arcpy.Intersect_analysis(in_features = age_fc + " #;" + tem_fc + " #", out_feature_class = intersect_fc, 
                                 join_attributes = "ALL", cluster_tolerance = "-1 Unknown", output_type = "INPUT")
        row_total = int(arcpy.GetCount_management(intersect_fc).getOutput(0))
        if row_total > 0:
            logging.info("Reading Intersect output feature class table to dictionary")
            row_count = 0
            for row in arcpy.da.SearchCursor(intersect_fc, ["TEIS_ID", age_field, "SHAPE@AREA"]):
                row_count += 1
                try:
                    age_cl_sts_dict[row[0]][calc_age_cl_sts(row[1])] += row[2]
                except:
                    try:
                        age_cl_sts_dict[row[0]][calc_age_cl_sts(row[1])] = row[2]
                    except:
                        age_cl_sts_dict[row[0]] = {}
                        age_cl_sts_dict[row[0]][calc_age_cl_sts(row[1])] = row[2]
                if row_count % 100000 == 0 or row_count == row_total:
                    logging.info("    Read " + str(row_count) + " of " + str(row_total) + " rows")
        else:
            arcpy.Delete_management(intersect_fc)
            logging.error("Intersection is empty; VRI and PEM/tem feature classes do not overlap. Exiting.")
            sys.exit()

    tem_fields = [f.name for f in arcpy.ListFields(tem_fc)]
    x = 1
    fields_added = False
    while not fields_added:
        age_cl_sts_field = "AGE" + str(x) + "_CL_STS"
        age_cl_std_field = "AGE" + str(x) + "_CL_STD"
        if age_cl_sts_field not in tem_fields and age_cl_std_field not in tem_fields:
            logging.info("Adding new fields AGE" + str(x) + "_CL_STS and AGE" + str(x) + "_CL_STD")
            arcpy.AddField_management(tem_fc, age_cl_sts_field, "SHORT")
            arcpy.AddField_management(tem_fc, age_cl_std_field, "SHORT")
            fields_added = True
        else:
            x += 1

    row_count = 0
    no_age_count = 0
    row_total = int(arcpy.GetCount_management(tem_fc).getOutput(0))
    logging.info("Writing age class values to " + age_cl_sts_field + " and " + age_cl_std_field + " fields in " 
                 + tem_fc)
    with arcpy.da.UpdateCursor(tem_fc,["TEIS_ID", age_cl_sts_field, age_cl_std_field]) as cursor:
        for row in cursor:
            row_count += 1
            try:
                biggest_age_cl_sts = max(age_cl_sts_dict[row[0]].iteritems(), key=operator.itemgetter(1))[0]    
                ## see http://stackoverflow.com/questions/268272/getting-key-with-maximum-value-in-dictionary
                row[1] = biggest_age_cl_sts
                row[2] = calc_age_cl_std(biggest_age_cl_sts)
            except:
                # if the current polygon had no entry in the dictionary, then there is no
                # age class info for the polygon, so assign it values of -1.
                row[1] = -1
                row[2] = -1
                no_age_count += 1
            cursor.updateRow(row)
            if row_count % 100000 == 0 or row_count == row_total:
                logging.info("    Processed " + str(row_count) + " of " + str(row_total) + " rows")
        if no_age_count == 0:
            logging.info("All " + str(row_total) + " tem polygon(s) overlapped with an age polygon. That's good!")
        else:
            logging.info("**** WARNING: There were " + str(no_age_count) + " polygon(s) for which age classes could "
                         "not be calculated. These polygons probably don't overlap with any polygons in the age "
                         "feature class.")
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
        parser = ArgumentParser(description='This script adds new age class fields to a tem feature class '
                                            'and populates the new fields based on ages in a second feature class ',
                                formatter_class=RawTextHelpFormatter)
        parser.add_argument('bfc', help='tem feature class')
        parser.add_argument('afc', help='Polygon feature class containing age data')
        parser.add_argument('afl', help='Name of field that contains age values in age feature class')
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
        main(args.bfc, args.afc, args.afl)

    except Exception as e:
        logging.exception('Unexpected exception. Program terminating.')
else:
    import arcpy
