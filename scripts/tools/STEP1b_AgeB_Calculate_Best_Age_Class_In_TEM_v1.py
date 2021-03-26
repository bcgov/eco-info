"""

Original Author:
Madrone (Jeff Kruys)

Created on:
2021-01-23

Purpose:
This script calculates the "best" values for AGE_CL_STS and AGE_CL_STD fields
in a tem feature class. User must specify a tem feature class and a list of 
"source" age class (for STS) fields that are already in the tem attribute table, 
in order of highest to lowest priority. The list of fields should be entered
at the command prompt as a comma-delimited string, beginning and ending with
double-quote mark, and no spaces. E.g. "AGE1_CL_STS,VRI_AGE_STS,AGE2_CL_STS".
For each STS field specified, there must also be a corresponding STD field.

Usage:
Calculate_Best_Age_Class_In_tem.py bfc afl [-h] [-l] [-ld]

Positional Arguments:
   bfc              tem feature class or table
   afl              List of fields that contains age class values for STS
   
Optional Arguments:
  -h, --help       show this help message and exit
  -l, --level      log level messages to display; Default: 20 - INFO
  -ld, --log_dir   path to directory for output log file

Example Input:
X:\fullpath\Calculate_Best_Age_Class_In_tem.py Y:\fullpath\bfc "age_field_1,age_field_2"


History
2021-01-23 (JK): Created script.
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

def main(tem_fc, age_field_list_str):
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
    # Check that input feature class exists and contains required fields
    # ---------------------------------------------------------------------------------------------------------

    if not arcpy.Exists(tem_fc):
        logging.error("**** Specified tem feature class " + tem_fc + " does not exist. Exiting script.")
        sys.exit()

    age_field_list = age_field_list_str.split(",")

    age_field_found = False
    cfl = []
    missing_fields = []
    tem_fields = [f.name for f in arcpy.ListFields(tem_fc)]
    for age_field in age_field_list:
        if age_field not in tem_fields:
            missing_fields.append(age_field)
        if age_field.replace("STS", "STD") not in tem_fields:
            missing_fields.append(age_field.replace("STS", "STD"))
        cfl.append(age_field)
        cfl.append(age_field.replace("STS", "STD"))
    if len(missing_fields) > 0:
        logging.error("**** Specified tem feature class is missing required fields: " 
                      + str(missing_fields.replace("[", "").replace("]", "").replace("'", "")))

    for age_field in ["AGE_CL_STS", "AGE_CL_STD"]:
        if age_field not in tem_fields:
            logging.info("Adding field " + age_field + " to tem feature class")
            arcpy.AddField_management(tem_fc, age_field, "SHORT")
        cfl.append(age_field)

    # ---------------------------------------------------------------------------------------------------------
    # For each polygon, copy from the first specified pair of fields (STS and STD) to AGE_CL_STS and AGE_CL_STD.
    # If they are -1 or Null, then copy from the second specified pair of fields. And son on.
    # ---------------------------------------------------------------------------------------------------------

    logging.info("Writing the best age class values to AGE_CL_STS and AGE_CL_STD")

    row_count = 0
    row_total = int(arcpy.GetCount_management(tem_fc).getOutput(0))
    with arcpy.da.UpdateCursor(tem_fc, cfl) as cursor:
        for row in cursor:
            row_count += 1
            x = 0
            age_fields_written = False
            while age_fields_written == False and x <= len(age_field_list) - 1:
                if row[cfl.index(age_field_list[x])] not in [-1, None] and row[
                        cfl.index(age_field_list[x].replace("STS", "STD"))] not in [-1, None]:
                    row[cfl.index("AGE_CL_STS")] = row[cfl.index(age_field_list[x])]
                    row[cfl.index("AGE_CL_STD")] = row[cfl.index(age_field_list[x].replace("STS", "STD"))]
                    age_fields_written = True
                else:
                    x += 1
            if not age_fields_written:
                row[cfl.index("AGE_CL_STS")] = -1
                row[cfl.index("AGE_CL_STD")] = -1
            cursor.updateRow(row)
            if row_count % 100000 == 0 or row_count == row_total:
                logging.info("    Processed " + str(row_count) + " of " + str(row_total) + " rows")

    # ---------------------------------------------------------------------------------------------------------
    # Done
    # ---------------------------------------------------------------------------------------------------------

    dtCalcNow = time.time()
    dtCalcScriptElapsed = dtCalcNow - dtCalcScriptStart
    logging.info("Script complete after " + SanitizeElapsedTime(dtCalcScriptElapsed))

if __name__ == '__main__':
    try:
        # Parse arguments
        parser = ArgumentParser(description='This script populates AGE_CL_STD and AGE_CL_STD fields of a '
                                            'tem feature class with values from a list of other age class '
                                            'fields as specified by the user in high to low priority order.',
                                formatter_class=RawTextHelpFormatter)
        parser.add_argument('bfc', help='tem feature class')
        parser.add_argument('afl', help='Comma-delimited list of age class (for STS) fields in order of '
                                        ' priority, highest to lowest.')
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
        main(args.bfc, args.afl)

    except Exception as e:
        logging.exception('Unexpected exception. Program terminating.')
else:
    import arcpy
