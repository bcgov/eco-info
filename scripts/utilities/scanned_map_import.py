"""
For documentation on this script, run with -h flag
"""

import sys
import os
import time
import logging
import openpyxl

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
    input_xls, smm_fc, mg_fc, logger = get_input_parameter()
    append_scanned_maps(input_xls, smm_fc, mg_fc, logger)


def get_input_parameter():
    try:
        # Parse arguments
        parser = ArgumentParser(description='This script appends new polygons to the Scanned Maps Master feature '
                                            'class based on a specified Scanned Map Input Excel file.',
                                formatter_class=RawTextHelpFormatter)
        parser.add_argument('xls', help='Input Scanned Map Input Excel file')
        parser.add_argument('sfc', help='Scanned Maps Master feature class')
        parser.add_argument('mfc', help='Mapsheet Grid feature class')
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


def append_scanned_maps(input_xls, smm_fc, mg_fc, logger):
    if not os.path.isfile(input_xls):
        logger.error('Specified input Excel file does not exist. Exiting script.')
        sys.exit(100)

    if not arcpy.Exists(smm_fc):
        logger.error('Specified Scanned Maps Master feature class does not exist. Exiting script.')
        sys.exit(100)

    smm_fc_f = [f.name for f in arcpy.ListFields(smm_fc) if not f.required]
    if 'FILE_NAME' not in smm_fc_f:
        logger.error('Specified Scanned Maps Master feature class does not contain required field FILE_NAME. Exiting '
                     'script.')
        sys.exit(100)

    if not arcpy.Exists(mg_fc):
        logger.error('Specified Mapsheet Grid feature class does not exist. Exiting script.')
        sys.exit(100)

    mg_fc_f = [f.name for f in arcpy.ListFields(mg_fc) if not f.required]
    if 'MAP_TILE' not in mg_fc_f:
        logger.error('Specified Mapsheet Grid feature class does not contain required field MAP_TILE. Exiting script.')
        sys.exit(100)

    try:
        logger.info('Loading Excel file')
        wb = openpyxl.load_workbook(input_xls)
    except:
        logger.error('Specified input file is not a valid Excel file. Exiting script.')
        sys.exit(100)

    sheet_name = 'Data_Entry_Template'
    try:
        sheet = wb.get_sheet_by_name(sheet_name)
    except:
        logger.error('Input Excel file does not contain required worksheet {}. Exiting script.'.format(sheet_name))
        sys.exit(100)

    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    columns = []
    for letter in alphabet:
        columns.append(letter)
    for letter1 in alphabet:
        for letter2 in alphabet:
            columns.append(letter1 + letter2)

    xls_head_col_dict = {}
    for column in columns:
        header = sheet["{}1".format(column)].value
        if header in ["", None]:
            break
        else:
            xls_head_col_dict[header] = column

    if 'MAPSH_LST' not in xls_head_col_dict.keys():
        logger.error('Input Excel file does not contain required field MAPSH_LST. Exiting script.')
        sys.exit(100)

    smm_field_dict = {}
    for smm_field in arcpy.ListFields(smm_fc):
        if not smm_field.required:
            smm_field_dict[smm_field.name] = {'TYPE': smm_field.type, 'LENGTH': smm_field.length}

    # Determine the fields that the Excel file and smm_fc have in common. Alert the user about
    # mismatched/missing field names.
    common_fields = list(set.intersection(set(xls_head_col_dict.keys()), set(smm_field_dict.keys())))
    xls_fields_unmatched = list(set(xls_head_col_dict.keys()).difference(set(smm_field_dict.keys())))
    smm_fields_unmatched = list(set(smm_field_dict.keys()).difference(set(xls_head_col_dict.keys())))

    if len(xls_fields_unmatched) > 0:
        logger.warning('Fields found in Excel file that are not in Scanned Maps Master:')
        for field in xls_fields_unmatched:
            logger.warning('  - {}'.format(field))
    if len(smm_fields_unmatched) > 0:
        logger.warning('Fields found in Scanned Maps Master that are not in Excel file:')
        for field in smm_fields_unmatched:
            logger.warning('  - {}'.format(field))

    # Read the MAPSH_LST column of the Excel table and compile a list of all mapsheets we will need to find
    # the geometry for.
    mapsh_geom_dict = {}
    mapsh_list = []
    xls_row = 1
    xls_row_empty = False
    mapsh_col = xls_head_col_dict['MAPSH_LST']
    logger.info('Reading mapsheet labels from MAPSH_LST column of Excel file')
    while not xls_row_empty:
        xls_row += 1
        if sheet["A{}".format(xls_row)].value in ['', None]:
            xls_row_empty = True
            logger.debug('Row {} of Excel table is empty.'.format(xls_row))
        else:
            mapsh_value = str(sheet['{}{}'.format(mapsh_col, xls_row)].value).replace('None', '').replace(' ', '')
            for mapsh in mapsh_value.split(','):
                mapsh_geom_dict[mapsh] = []
                mapsh_list.append(mapsh)
    logger.debug('Found {} unique mapsheets listed in column {} of Excel table'.format(len(mapsh_geom_dict.keys()),
            mapsh_col))

    # Read the geometries of each mapsheet found above from the mapsheet grid feature class
    cfl = ['MAP_TILE', 'SHAPE@']
    row_count = 0
    row_total = int(arcpy.GetCount_management(mg_fc).getOutput(0))
    found_count = 0
    logger.info('Reading {} geometries from {}'.format(len(mapsh_geom_dict.keys()), mg_fc))
    for row in arcpy.da.SearchCursor(mg_fc, cfl):
        row_count += 1
        try:
            mapsh_geom_dict[row[0]].append(row[1])
        except:
            pass
        if row_count % 100000 == 0 or row_count == row_total:
            found_count = len([mapsh for mapsh in mapsh_geom_dict.keys() if len(mapsh_geom_dict[mapsh]) > 0])
            logger.debug('    Read {} of {} rows, found {} of {} mapsheets'.format(row_count, row_total, found_count, 
                len(mapsh_geom_dict.keys())))
    invalid_mapsheets = []
    for mapsh in mapsh_geom_dict.keys():
        if mapsh_geom_dict[mapsh] == []:
            invalid_mapsheets.append(mapsh)
    if len(invalid_mapsheets) > 0:
        logger.error('Some mapsheets listed in MAPSH_LST column of Excel file are not found in BC Grid feature class:')
        # for invalid_mapsheet in invalid_mapsheets:
        #     logger.error(invalid_mapsheet)
        for mapsh in mapsh_list:
            if len(mapsh_geom_dict[mapsh]) == 0:
                logger.error('    - {} NOT FOUND'.format(mapsh))
            else:
                logger.error('    - {} found'.format(mapsh))
        sys.exit(100)

    # Define the cfl (cursor field list)
    cfl = []
    for common_field in common_fields:
        cfl.append(common_field)
    cfl.append("SHAPE@")
    
    # Loop through the Excel table and create a new feature (a list of attributes) for each row
    xls_row = 1
    xls_row_empty = False
    new_smm_rows = []
    invalid_values = []
    logger.info('Reading Excel table')
    while not xls_row_empty:
        xls_row += 1
        logger.debug('Reading row {} of Excel table'.format(xls_row))
        if sheet["A{}".format(xls_row)].value in ['', None]:
            xls_row_empty = True
            logger.debug('Row {} of Excel table is empty.'.format(xls_row))
        else:
            new_smm_row = []
            for common_field in common_fields:
                xls_col = xls_head_col_dict[common_field]
                value = sheet["{}{}".format(xls_col, xls_row)].value
                logger.debug("Excel sheet cell {}{} has value {}".format(xls_col, xls_row, value))
                # Currently the Scanned Maps Master feature class only has string, long int and short int fields,
                # so we will only validate for those field types.
                if smm_field_dict[common_field]['TYPE'] == 'SmallInteger':
                    if value in ['', None]:
                        new_smm_row.append(None)
                    else:
                        try:
                            x = int(value)
                            if -32768 <= value <= 32767:
                                new_smm_row.append(int(value))
                            else:
                                new_smm_row.append(None)
                                invalid_values.append("{}{}".format(xls_col, xls_row))
                        except:
                            new_smm_row.append(None)
                            invalid_values.append("{}{}".format(xls_col, xls_row))
                elif smm_field_dict[common_field]['TYPE'] == 'Integer':
                    if value in ['', None]:
                        new_smm_row.append(None)
                    else:
                        try:
                            x = int(value)
                            if -2147483648 <= value <= 2147483647:
                                new_smm_row.append(int(value))
                            else:
                                new_smm_row.append(None)
                                invalid_values.append("{}{}".format(xls_col, xls_row))
                        except:
                            new_smm_row.append(None)
                            invalid_values.append("{}{}".format(xls_col, xls_row))
                elif smm_field_dict[common_field]['TYPE'] == 'String':
                    if value in ['', None]:
                        new_smm_row.append('')
                    elif len(str(value)) <= smm_field_dict[common_field]['LENGTH']:
                        new_smm_row.append(str(value))
                    else:
                        new_smm_row.append(None)
                        invalid_values.append("{}{}".format(xls_col, xls_row))

            logger.debug('New row will look like {}'.format(new_smm_row))
            # Now grab the geometry from the dictionary mapsh_geom_dict[mapsh][0] (it's a list of one geometry object)
            mapsh_col = xls_head_col_dict['MAPSH_LST']
            value = str(sheet['{}{}'.format(mapsh_col, xls_row)].value).replace('None', '').replace(' ', '')
            if ',' not in value:
                mapsh_geom = mapsh_geom_dict[value][0]
            else:
                mapsh_geom = mapsh_geom_dict[value.split(',')[0]][0]
                for mapsh in value.split(',')[1:]:
                    mapsh_geom = mapsh_geom.union(mapsh_geom_dict[mapsh][0])

            new_smm_row.append(mapsh_geom)
            new_smm_rows.append(new_smm_row)
        logger.debug('Processed {} rows of Excel table'.format(xls_row))

    if len(invalid_values) > 0:
        if len(invalid_values) > 0:
            logger.error('Invalid values found in the following Excel sheet cells: {}'.format(
                    str(invalid_values).replace('[', '').replace(']', '').replace("'", '')))
        sys.exit(100)

    icursor = arcpy.da.InsertCursor(smm_fc, cfl)
    logger.debug('Initiating InsertCursor with the following fields:')
    for f in cfl:
        logger.debug('  - {}'.format(f))
    logger.info('Inserting {} new rows into Scanned Maps Master feature class.'.format(len(new_smm_rows)))
    for new_smm_row in new_smm_rows:
        icursor.insertRow(new_smm_row)


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
