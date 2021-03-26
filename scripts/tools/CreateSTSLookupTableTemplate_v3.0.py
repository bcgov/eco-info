"""
For documentation on this script, run with -h flag

Original Author:
Madrone (Jeff Kruys)

Created on:
2021-03-03

Purpose:
This script reads an input TEM/PEM/BEM feature class and 
creates an output Structural Stage LUT Template Excel file.

Usage:
02_CreateSTSLookupTableTemplate_20210303_new.py efc [-h] [-l] [-ld]

Positional Arguments:
   efc              Ecosystem mapping (TEM/PEM/BEM) feature class
   
Optional Arguments:
  -h, --help       show this help message and exit
  -l, --level      log level messages to display; Default: 20 - INFO
  -ld, --log_dir   path to directory for output log file

Example Input:
X:\fullpath\02_CreateSTSLookupTableTemplate_20210303_new.py Y:\fullpath\efc

History:
2021-03-03 (JK): Created script based on older version of 02_CreateSTSLookupTableTemplate.py.
                 New version follows PEP8 scripting standards, writes output in .xlsx format
                 instead of .csv, and takes input feature class as an argument.
"""

import sys
import os
import time
import logging
import openpyxl
import pdb

from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from datetime import datetime as dt


class ArcPyLogHandler(logging.StreamHandler):
    """
    Custom logging class that bounces messages to the arcpy tool window as well
    as reflecting back to the file.
    """

    def emit(self, record):
        """
        Write the log message
        """
        try:
            msg = record.msg.format(record.args)
        except:
            msg = record.msg

        if record.levelno == logging.ERROR:
            arcpy.AddError(msg)
        elif record.levelno == logging.WARNING:
            arcpy.AddWarning(msg)
        elif record.levelno == logging.INFO:
            arcpy.AddMessage(msg)
        else:
            arcpy.AddMessage(msg)

        super(ArcPyLogHandler, self).emit(record)


def run_app():
    in_fc, logger = get_input_parameter()
    create_sts_lut(in_fc, logger)


def SanitizeElapsedTime(dtInput):
    if dtInput < 120:
        strElapsedTime = str(int(dtInput)) + ' sec.'
    elif dtInput < 3600:
        strElapsedTime = str(round(dtInput / 60, 1)) + ' min.'
    else:
        strElapsedTime = str(round(dtInput / 3600, 2)) + ' hr.'
    return strElapsedTime


def get_input_parameter():
    try:
        # Parse arguments
        parser = ArgumentParser(description='This script reads an input feature class and writes an Excel file '
                                            'containing a Structural Stage Lookup Table template.',
                                formatter_class=RawTextHelpFormatter)
        parser.add_argument('xls', help='Input Ecosystem Mapping feature class')
        parser.add_argument('--log_level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                            help='Log level')
        parser.add_argument('--log_dir', help='Path to log Directory')
        args = parser.parse_args()

        log_name = 'main_logger'
        logger = logging.getLogger(log_name)
        logger.handlers = []

        log_fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        log_file_base_name = os.path.basename(sys.argv[0])
        log_file_extension = 'log'
        timestamp = dt.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_file = "{}_{}.{}".format(timestamp, log_file_base_name, log_file_extension)

        logger.setLevel(args.log_level)

        sh = logging.StreamHandler()
        sh.setLevel(args.log_level)
        sh.setFormatter(log_fmt)
        logger.addHandler(sh)

        if args.log_dir:
            try:
                os.makedirs(args.log_dir)
            except OSError:
                pass

            fh = logging.FileHandler(os.path.join(args.log_dir, log_file))
            fh.setLevel('DEBUG')
            fh.setFormatter(log_fmt)
            logger.addHandler(fh)

        if os.path.basename(sys.executable).lower() == 'python.exe':
            arc_env = False
        else:
            arc_env = True

        if arc_env:
            arc_handler = ArcPyLogHandler()
            arc_handler.setLevel(args.log_level)
            arc_handler.setFormatter(log_fmt)
            logger.addHandler(arc_handler)

        # Start the script
        return args.xls, args.sfc, args.mfc, logger

    except Exception as e:
        print('Unexpected exception. Program terminating.')
        exit(1)


def append_scanned_maps(in_fc, logger):
    if not arcpy.Exists(in_fc):
        logger.error('Specified Ecosystem Mapping feature class does not exist. Exiting script.')
        sys.exit(100)

    cfl = ['BGC_ZONE', 'BGC_SUBZON', 'BGC_VRT', 'BGC_PHASE', 'SDEC_1', 'SDEC_2', 'SDEC_3', 'SITE_S1', 'SITE_S2', 
                  'SITE_S3', 'SITEMC_S1', 'SITEMC_S2', 'SITEMC_S3']
    in_f_list = [f.name for f in arcpy.ListFields(in_fc)]
    missing_f_list = []
    for f in in_f_list:
        if f not in cfl:
            missing_f_list.append(f)
    if len(missing_f_list) > 0:
        logger.error('Input feature class is missing the following required fields: {}. Exiting script.'.format(
            str(missing_f_list).replace('[', '').replace(']', '').replace("'", '')))
        sys.exit(100)

    logger.info('Reading the input feature class')

    unique_eco_dict = {}
    row_count = 0
    row_total = int(arcpy.GetCount_management(in_fc).getOutput(0))
    with arcpy.da.SearchCursor(in_fc, cfl) as cursor:
        for row in cursor:
            row_count += 1
            for i in range(1, 4):
                if row[cfl.index("SDEC_{}".format(i))] > 0:
                    key_list = []
                    key_list.append(str(row[cfl.index("BGC_ZONE")]).replace('None','').replace(' ',''))
                    key_list.append(str(row[cfl.index("BGC_SUBZON")]).replace('None','').replace(' ',''))
                    key_list.append(str(row[cfl.index("BGC_VRT")]).replace('None','').replace('0',''))
                    key_list.append(str(row[cfl.index("BGC_PHASE")]).replace('None','').replace(' ',''))
                    key_list.append(str(row[cfl.index("SITE_S{}".format(i))]).replace('None','').replace(' ',''))
                    key_list.append(str(row[cfl.index("SITEMC_S{}".format(i))]).replace('None','').replace(' ',''))
                    key_str = str(key_list)
                    try:
                        unique_eco_dict[key_str] += 1
                    except:
                        unique_eco_dict[key_str] = 1

            if row_count % 100000 == 0 or row_count == row_total:
                logger.info('    Read {} of {} records ({} unique ecosystems found)'.format(row_count, row_total, 
                    len(unique_eco_dict.keys())))

    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    columns = []
    for letter in alphabet:
        columns.append(letter)
    for letter1 in alphabet:
        for letter2 in alphabet:
            columns.append(letter1 + letter2)

    fgdb_parent_folder = os.path.split(os.path.split(in_fc)[0])[0]
    out_xlsx = os.path.join(fgdb_parent_folder, 
                            'WHR_STS_Lookup_Table_Template_{}.csv'.format(time.strftime("%Y%m%d_%H%M%S")))

    logging.info("Writing output file {}".format(out_xlsx))
    wb = openpyxl.Workbook()
    wb.save(out_xlsx)
    sheet = wb.get_sheet_by_name("Sheet")

    header_list = ['FREQ', 'Bgc_zone', 'Bgc_subzon', 'Bgc_vrt', 'Bgc_phase', 'BEC_Label', 'ECOS_C', 'SITE_S', 
                   'SITEMC_S', 'Site Series Name', 'Plant Community Name', 'Habitat_Subtype', 'Ecosystem_Description', 
                   'Realm', 'Group', 'Class', 'Kind', 'Forested', 'Non-Productive Forest Unit', 
                   'Default to original STS', 'Default_STS', 'STS_Range', 'STS_Climax', 'SComp_Climax', 
                   'SComp_Age_1-15', 'SComp_Age_16-30', 'SComp_Age_31-50', 'SComp_Age_51-80', 'SComp_Age_>80', 
                   'STS_Age_0-2', 'STS_Age_3-5', 'STS_Age_6-10', 'STS_Age_11-20', 'STS_Age_21-40', 'STS_Age_41-60', 
                   'STS_Age_61-80', 'STS_Age_81-100', 'STS_Age_101-120', 'STS_Age_121-140', 'STS_Age_141-180', 
                   'STS_Age_181-200', 'STS_Age_201-250', 'STS_Age_251-399', 'STS_Age_400+', 'SS2_Age_Max', 
                   'STS3a_Age_Max', 'STS3b_Age_Max', 'STS4_Age_Max', 'STS5_Age_Max', 'STS6_Age_Max', 'STS7_Age_Min', 
                   'STS7a_Max', 'STS7b_Min', 'STS7d_Min', 'Short_Term_Trend_Age', 'Long_Term_Trend_Age']
    i = 0
    for header in header_list:
        sheet[columns[i] + "1"].value = header
        i += 1

    row = 1
    for key_str in sorted(set(unique_eco_dict.keys())):
        row += 1
        key_list = ast.literal_eval(key_str)
        for i in range(0, len(key_list)):
            sheet["{}{}".format(columns[i], row)].value = str(key_list[i])

    logging.info("Wrote {} rows to output file {}".format(row, out_xlsx))
    wb.save(out_xlsx)

if __name__ == '__main__':
    try:
        # Import arcpy
        import arcpy
    except:
        logging.error('No ArcGIS licenses available to run this tool.  Program terminating.')
        sys.exit(1)
    run_app()
else:
    try:
        # Import arcpy
        import arcpy
    except:
        logging.error('No ArcGIS licenses available to run this tool.  Program terminating.')
        sys.exit(1)
