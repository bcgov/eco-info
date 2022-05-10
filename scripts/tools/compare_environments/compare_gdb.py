# ================================================================================================================
# Title: compare_gdb.py
# Author: Conor MacNaughton (idir: cmacnaug)
# Date created: 2022/03/25
# Date updated:
# Description: For comparison/QA of two geodatabases. Points out features that exist in one gdb and not the other,
#              then compares the spatial reference, schema, and attributes of same-name features by calling a
#              collection of functions from compare_feature.py.
# Python Version: 3.7
# ================================================================================================================

import arcpy as ap
import os
import sys
from compare_feature import *
from datetime import datetime as dt


def compare_gdb(gdb_list, output_loc):
    """Given a list containing the paths of two identically named geodatabases, perform high-level comparison of their items
    and call functions from compare_feature.py to compare spatial reference, schema, and attributes of same-name items.
    Shows findings with standard output stream (print or log) and calls compile_report to create an Excel file of results."
    \nParameters:
    \tgdb_list (list): list of paths of gdbs to compare. eg. [r'X:\TEIS_Env_Master\Operational_Data.gdb', r'X:\Deliverables\Operational_Data.gdb']
    \toutput_loc (path): the location to save Excel file and log"""

    ap.env.overwriteOutput = True

    # a list of feature class or table names to omit from comparison (change as required)
    omit_list = ['User_Defined', 'CriticalFieldErrors', 'CriticalRangeErrors', 'DomainErrors',
                 'GeometryErrors', 'RangeErrors', 'RowErrors', 'SummaryErrors']

    # create output directory
    if os.path.basename(os.path.normpath(gdb_list[0])) == os.path.basename(os.path.normpath(gdb_list[1])):
        gdb_name = os.path.basename(
            os.path.normpath(gdb_list[0])).rstrip('.gdb')
    elif os.path.basename(os.path.normpath(gdb_list[0])) != os.path.basename(os.path.normpath(gdb_list[1])):
        gdb_name = os.path.basename(os.path.normpath(gdb_list[0])).rstrip('.gdb') + '_' + \
            os.path.basename(os.path.normpath(gdb_list[1])).rstrip('.gdb')
    out_dir = os.path.join(output_loc, gdb_name + '_Compare_Files')
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    # create log file and change system standard output to log instead of printing to console/terminal
    log = open(os.path.join(out_dir, 'comparison_rpt.log'), 'w')
    sys.stdout = log

    print('\nCOMPARING {} to {}'.format(gdb_list[0], gdb_list[1]))
    print('Started at: ', dt.now())

    # create dictionaries for common items and unique items
    all_items = []
    for g in gdb_list:
        ap.env.workspace = g
        all_items.extend((ap.ListFeatureClasses(), ap.ListTables()))

    common_dict = {'feature_classes': set(all_items[0]).intersection(set(all_items[2])),
                   'tables': set(all_items[1]).intersection(set(all_items[3]))}

    diff_dict = {gdb_list[0]: [set(all_items[0]).difference(set(all_items[2])),
                               set(all_items[1]).difference(set(all_items[3]))],
                 gdb_list[1]: [set(all_items[2]).difference(set(all_items[0])),
                               set(all_items[3]).difference(set(all_items[1]))]}
    for k, v in diff_dict.items():
        print('\n\tFeatures classe(s) unique to {}: \n\t{}'.format(
            k, v[0]) if len(v[0]) != 0 else '')
        print('\n\tTable(s) unique to {}: \n\t{}'.format(
            k, v[1]) if len(v[1]) != 0 else '')

    # iterate through common feature classes and compare spatial reference, schema, and attributes
    # (calling functions from compare_feature.py)
    df_list = []
    for fc in (fc for fc in sorted(common_dict['feature_classes']) if not any(o in fc for o in omit_list)):
        print('\nComparing feature class: {}'.format(fc))
        base_fc = gdb_list[0]+'\\'+fc
        test_fc = gdb_list[1]+'\\'+fc
        fc_list = [base_fc, test_fc]

        sr_compare(fc_list)

        schema_df = schema_compare(fc_list)
        if schema_df is not None:
            df_list.append(schema_df)
            print('\tSchemas do not match. See Excel report.')
        elif schema_df is None:
            print('\tSchemas match.')
        try:
            attributes_dfs = attributes_compare(fc_list)
            if attributes_dfs is not None:
                df_list.extend(attributes_dfs)
        except:
            print('An ')
            pass

    # iterate through common tables and compare spatial reference, schema, and attributes
    # (calling functions from compare_feature.py)
    for table in (table for table in sorted(common_dict['tables']) if not any(o in table for o in omit_list)):
        print('\nComparing table: {}'.format(table))
        base_table = gdb_list[0]+'\\'+table
        test_table = gdb_list[1]+'\\'+table
        table_list = [base_table, test_table]

        schema_df = schema_compare(table_list)
        if schema_df is not None:
            df_list.append(schema_df)
            print('\tSchemas do not match. See Excel report.')
        elif schema_df is None:
            print('\tSchemas match.')

        attributes_dfs = attributes_compare(table_list)
        if attributes_dfs is not None:
            df_list.extend(attributes_dfs)

    print('\nGeodatabase comparison completed at: ', dt.now())

    # export list of dataframes to Excel
    if df_list:
        to_export = [df for df in df_list if df.shape[0] <= 100000]
        for df in (df for df in df_list if df.shape[0] > 100000):
            to_export.extend(split_dataframe(df))
        compile_report(gdb_name, to_export, out_dir)
        print('Export completed at: ', dt.now())
