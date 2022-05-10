# ================================================================================================================
# Title: compare_feature.py
# Author: Conor MacNaughton (idir: cmacnaug)
# Date created: 2022/03/25
# Date updated:
# Description: Collection of functions for QA/comparison of geodatabase features (feature classes and tables).
#          These were created to be called by the compare_gdb.py script, but are suited for use elsewhere.
# ================================================================================================================

import traceback
import os
import arcpy as ap
import pandas as pd
import numpy as np
import more_itertools as mit
from collections import defaultdict
import xlsxwriter
import xlwt

def split_dataframe(df, chunk_size=1000000):
    """Split large dataframes into smaller chunks so that they can be exported to Excel.
    \nParameters:
    \tdf (dataframe): dataframe to be split
    \nchunk_size (int): the number of records to split off into each chunk
    \nReturns:
    \tchunks (list): list of dataframes (chunks)"""
    chunks = list()
    num_chunks = df.shape[0] // chunk_size + 1
    for i in range(num_chunks):
        chunks.append(df[i*chunk_size:(i+1)*chunk_size])
    for n, chunk in enumerate(chunks):
        chunk.name = df.name + '_' + str(n + 1)
    return chunks


def trunc_xlsx_sheet_name(name):
    """Truncate the name given to an Excel sheet by stripping chars from the left of a string if it has > 31 chars. Excel sheet names must be <= 31 chars.
    \nParameters:
    \tname (str): name to be given
    \nReturns:
    \n\tname (str): truncated name
    \tor
    \tname (str): original name if string is <= 31 chars"""
    if len(name) > 29:
        n = len(name) - 29
        name = name.lstrip(name[:n])

        return name
    else:
        return name


def insert_dummy_rows(uid_list):
    """Given a list of lists representing runs of consecutive integers (usually a unique ID), calculate the missing intervals.
    eg. find missing unique IDs (gaps) in a dataframe"
    \nParameters:
    \tuid_list (list(int) of lists): runs of consecutive integers
    \nReturns:
    \n\tmissing (list): list of missing integers"""
    missing = []
    for i in range(len(uid_list)-1):
        n = min(uid_list[i+1]) - max(uid_list[i])-1
        for x in range(n-(n-1), n+1):
            missing.append(max(uid_list[i]) + x)

    return missing


def dataframe_compare(df_list):
    """Given a list containing two pandas dataframes, compare their attributes.
    Shows findings with standard output stream (print or log) and dataframes."
    \nParameters:
    \tdf_list (list): list of dataframes to compare. Could be full feature class attribute table, gdb tables, or a BAPID.
    \nReturns:
    \n\treturn_list (list): list of dataframes"""
    try:
        col_dict = {}
        return_list = []

        # merge the two features dataframes
        combined_df = pd.merge(df_list[0], df_list[1], how='outer', left_index=True,
                               right_index=True, suffixes=('_b', '_t'), indicator=True)
        combined_df.name = str(df_list[0].name)

        # create boolean variable to trigger BAPID-specific operations if necessary 
        if 'BAPID_b' in combined_df.columns:
            bapid_check = True
        else:
            bapid_check = False

        if bapid_check:
            # make sure the PROJPOLYID field is called that
            if any('PROJECT_POLYGON_IDENTIFIER' in col for col in combined_df.columns):
                combined_df.rename(
                    {'PROJECT_POLYGON_IDENTIFIER_b': 'PROJPOLYID_b', 'PROJECT_POLYGON_IDENTIFIER_t': 'PROJPOLYID_t'}, axis=1, inplace=True)
            # build list of PROJPOLYIDs found in one feature but not the other
            if any('PROJPOLYID' in col for col in combined_df.columns):
                base_ppid = list(combined_df['PROJPOLYID_b'].dropna().unique())
                test_ppid = list(combined_df['PROJPOLYID_t'].dropna().unique())
                base_only_ppid = set(base_ppid).difference(set(test_ppid))
                test_only_ppid = set(test_ppid).difference(set(base_ppid))
                if len(base_ppid) != len(test_ppid):
                    print('\tThere are {} PROJPOLYID(s) from {} in base feature.'.format(
                        len(base_ppid), combined_df.name))
                    print('\tThere are {} PROJPOLYID(s) from {} in test feature.'.format(
                        len(test_ppid), combined_df.name))
                if base_only_ppid:
                    print('\t{} PROJPOLYID(s) from {} found only in base feature: {}. \n\t Dropping to facilitate comparison.'.format(len(base_only_ppid), combined_df.name,
                                                                                                                                    sorted(base_only_ppid)))
                    combined_df = combined_df[~combined_df['PROJPOLYID_b'].isin(base_only_ppid)]
                    combined_df.name = str(df_list[0].name)                                                                                                                
                if test_only_ppid:
                    print('\t{} PROJPOLYID(s) from {} found only in test feature: {}. Dropping to facilitate comparison.'.format(len(test_only_ppid), combined_df.name,
                                                                                                                                sorted(test_only_ppid)))
                    combined_df = combined_df[~combined_df['PROJPOLYID_t'].isin(test_only_ppid)]
                    combined_df.name = str(df_list[0].name)
        
        # at present nothing is being done with 'left only' (aka 'base only') records
        if 'left_only' in combined_df._merge.values:
            base_only = combined_df[combined_df.columns[~combined_df.columns.str.endswith(
                '_t')]]
            base_only = base_only[base_only['_merge'] == 'left_only']

        # identify duplicates (BAPID and PROJPOLYID) in test feature and append dataframe of duplicates to return list
        if 'right_only' in combined_df._merge.values:
            test_only = combined_df[combined_df.columns[~combined_df.columns.str.endswith(
                '_b')]]
            test_only = test_only[test_only['_merge'] == 'right_only']
            if 'BAPID_t' in test_only.columns and 'PROJPOLYID_t' in test_only.columns:
                duplicates = test_only[test_only.duplicated(['BAPID_t', 'PROJPOLYID_t'], keep=False)][[
                    'BAPID_t', 'PROJPOLYID_t']].sort_values(['BAPID_t', 'PROJPOLYID_t'])
                if not duplicates.empty:
                    duplicates.name = trunc_xlsx_sheet_name(
                        combined_df.name + '_test_dup')
                    return_list.append(duplicates)
                    print('\tDuplicates found in {}. See Excel report.'.format(
                        feature_list[1]))
        
        # for records found in both features, split back out to base and test
        if 'both' in combined_df._merge.values:
            base = combined_df[combined_df.columns[~combined_df.columns.str.endswith(
                '_t')]].query('_merge == "both"')
            base.drop('_merge', axis=1, inplace=True)
            base.columns = base.columns.str[:-2]
            test = combined_df[combined_df.columns[~combined_df.columns.str.endswith(
                '_b')]].query('_merge == "both"')
            test.drop('_merge', axis=1, inplace=True)
            test.columns = test.columns.str[:-2]

            # use pandas not equal comparison of base and test dataframes for records common to features
            not_equal = base.ne(test)
            if True in not_equal.values:
                # find columns where all values are mismatched
                drop_ne = [
                    col for col in not_equal.columns if not_equal[col].all()]
                if drop_ne:
                    col_dict['all_vals_mismatched'] = drop_ne
                    if not bapid_check:
                        print(
                            '\n\tDropping columns where all values are mismatched to facilitate comparison. See Excel report.')
                # find columns where all values match
                drop_eq = [
                    col for col in not_equal.columns if not not_equal[col].any()]
                # if drop_eq:
                #     col_dict['all_vals_match'] = drop_eq
                # print(
                #     '\n\tDropping columns where all values match to facilitate comparison. See Excel report.')
                
                # create dataframe of columns where all values match and/or all values mismatched and append to return list
                if col_dict:
                    cols_df = pd.DataFrame.from_dict(col_dict, orient='index')
                    cols_df = cols_df.transpose()
                    if bapid_check:
                        cols_df['BAPID'] = combined_df.name.lstrip('BAPID_')
                    cols_df.name = trunc_xlsx_sheet_name(
                        combined_df.name + '_cols')
                    return_list.append(cols_df)

                # drop columns where all values match or all values are mismatched to facilitate comparison
                to_drop = drop_ne + drop_eq
                if to_drop:
                    base.drop(to_drop, axis=1, inplace=True)
                    test.drop(to_drop, axis=1, inplace=True)
                # check for inequality again after dropping columns
                not_equal = base.ne(test).any(axis=1)

                if True in not_equal.values:
                    comparison = pd.merge(base[not_equal], test[not_equal], how='outer',
                                          left_index=True, right_index=True, suffixes=('_b', '_t')).sort_index(axis=1)

                    # catch cases where a departure in correlation between the rows of the features being compared is likely
                    # not helpful to process and output each occurrence of inequality in such a case
                    if comparison.shape[0] >= 50000:
                        if 'BAPID' in combined_df.name:
                            comparison['index1'] = comparison.index
                            consec_count = comparison.groupby(
                                'index1')['index1'].count()
                            index_groups = [list(group)
                                            for group in mit.consecutive_groups(consec_count.index)]

                            for i in (i for i in index_groups if consec_count[i].sum() >= 50000):
                                print(
                                    """\tA run of over 50,000 attributes in consecutive records in {} 
                                    was mismatched. This usually indicates a departure in correlation between the rows
                                    of the features being compared. Records not exported to Excel.""".format(combined_df.name))
                                comparison.drop(i, inplace=True)
                        else:
                            consec_count = comparison.reset_index()
                            consec_count = consec_count.groupby(
                                'OBJECTID')['OBJECTID'].count()
                            index_groups = [list(group)
                                            for group in mit.consecutive_groups(consec_count.index)]

                            for i in (i for i in index_groups if consec_count[i].sum() >= 50000):
                                print(
                                    """\tA run of over 50,000 attributes in consecutive records, from OBJECTID {} to {}, 
                                    was mismatched. This usually indicates a departure in correlation between the OBJECTIDs
                                    of the features being compared. Records not exported to Excel.""".format(i[0], i[-1]))
                                comparison.drop(i, inplace=True)

                    # create dataframe showing the index, field, and test and base values that were found to be unequal and append to return list
                    if comparison.shape[0] != 0:
                        simplified = defaultdict(list)
                        for index, row in comparison.iterrows():
                            for label, content in row.items():
                                if label[-1] == 'b':
                                    simplified['index'].append(index)
                                    simplified['field'].append(
                                        label.rstrip(label[-2:]))
                                    simplified['base_val'].append(content)
                                if label[-1] == 't':
                                    simplified['test_val'].append(content)
                        simp_df = pd.DataFrame.from_dict(
                            simplified, orient='index').transpose().set_index('index')
                        simp_df = simp_df[simp_df['base_val']
                                          != simp_df['test_val']]
                        if bapid_check:
                            simp_df = simp_df.merge(combined_df[['OBJECTID_b', 'OBJECTID_t', 'BAPID_b']], how='left', left_index=True,
                                                    right_index=True)
                            simp_df = simp_df.rename(
                                {'OBJECTID_b': 'base_OBJECTID', 'OBJECTID_t': 'test_OBJECTID', 'BAPID_b': 'BAPID'}, axis=1)
                            simp_df = simp_df[[
                                'BAPID', 'base_OBJECTID', 'test_OBJECTID', 'field', 'base_val', 'test_val']]
                        simp_df.name = trunc_xlsx_sheet_name(
                            combined_df.name + '_att')
                        return_list.append(simp_df)
                        print(
                            '\tMismatched attributes still found for {} after dropping columns. See Excel report.'.format(combined_df.name))
        else:
            print('\tNo matching OBJECTIDs to compare.')

        if return_list:
            return return_list
        elif not return_list:
            return None

    except Exception as e:
        print('\tSomething went wrong during the attribute comparison for {}. \n\t{}. \n\tSkipping to next BAPID or feature.'.format(
            combined_df.name, traceback.format_exc()))
        pass


def attributes_compare(feature_list):
    """Given a list containing the paths of two identically named geodatabase features (ie. feature class, table), 
    perform high-level comparison of their attributes and set up dataframes for more detailed comparison with dataframe_compare function.
    Shows findings with standard output stream (print or log) and dataframes."
    \nParameters:
    \tfeature_list (list): list of paths. eg. [r'X:\TEIS_Env_Master\Operational_Data.gdb\TEIS_Master_Short_Tbl', r'X:\Deliverables\Operational_Data.gdb\TEIS_Master_Short_Tbl']
    \nReturns:
    \n\treturn_list (list): list of dataframes"""
    try:
        print('\tComparing attributes...')
        feature_name = os.path.basename(os.path.normpath(feature_list[0]))
        df_list = []
        return_list = []
        missing_dict = {}
        nulls_set = set()
        row_count = []
        null_types = {'Date': '1888-08-08', 'Double': -999.9, 'Float': -999.9,
                      'Integer': -9999, 'SmallInteger': -9999, 'String': ''}

        for feature in feature_list:
            # assign null fill types based on data type of field
            null_dict = {f.name: null_types[f.type] for f in ap.ListFields(
                feature) if f.type in null_types}
            for f in ap.ListFields(feature):
                if f.type == 'OID':
                    oid = f.name

            # read in attribute table (omitting geometry as these are read as tuples and will cause error)
            if ap.Describe(feature).datasetType == 'FeatureClass':
                df = pd.DataFrame(ap.da.FeatureClassToNumPyArray(feature, [f.name for f in ap.ListFields(feature) if f.name not in ['Shape', 'SHAPE', 'Geometry', 'GEOMETRY']],
                                                                 null_value=null_dict)).set_index(oid).sort_index()
            elif ap.Describe(feature).datasetType == 'Table':
                df = pd.DataFrame(ap.da.TableToNumPyArray(feature, [f.name for f in ap.ListFields(feature) if f.name not in ['Shape', 'SHAPE', 'Geometry', 'GEOMETRY']],
                                                          null_value=null_dict)).set_index(oid).sort_index()
            # if dataframe is empty, exit
            if df.shape[0] == 0:
                print('\t{} is empty. Ending attribute comparison.'.format(feature))
                return
            else:
                row_count.append(df.shape[0])

            # make sure the index is called OBJECTID to make things easier later on
            if df.index.name != 'OBJECTID':
                df.index.name = 'OBJECTID'

            # create list of null columns
            null_cols = [col for col in df.columns if df[col].isna(
            ).all() or df[col].isin(null_types.values()).all()]
            if null_cols:
                print('\tAll values are null in columns {} in {}. \n\tDropping from both features to facilitate comparison.'
                      .format(sorted(null_cols), feature))
                nulls_set.update(null_cols)

            # alter data types to decrease memory demand
            for col in df.columns:
                if not any(s in col for s in ['DATE', 'Date', 'date']) and df[col].dtypes == 'object' \
                        and df[col].nunique() <= 800:
                    df[col] = df[col].astype('category')
                # round floats so that Shape_Area and Shape_Length can be compared
                if df[col].dtypes == 'float64':
                    df[col] = df[col].round(2)
                    pd.to_numeric(df[col], errors='ignore', downcast='float')
                if df[col].dtypes == 'int32' or df[col].dtypes == 'int64':
                    df[col] = df[col].astype('Int64')

            df.name = trunc_xlsx_sheet_name(feature_name)
            df_list.append(df)

            # create list in dictionary of missing unique IDs (OBJECTIDs)
            uids = [list(group) for group in mit.consecutive_groups(df.index)]
            if len(uids) > 1:
                missing_dict[feature] = [
                    list(group) for group in mit.consecutive_groups(insert_dummy_rows(uids))]

        print('\t{} records in base.'.format(row_count[0]))
        print('\t{} records in test.'.format(row_count[1]))

        # drop nulls
        for df in df_list:
            if nulls_set:
                df.drop(nulls_set, axis=1, inplace=True)

        # ensure category type fields from both features have the same categories so they can be compared
        cat_dict = defaultdict(set)
        for df in df_list:
            for col in (col for col in df.columns if df[col].dtype.name == 'category'):
                cat_dict[col].update(df[col].cat.categories)
        for df in df_list:
            for col in (col for col in df.columns if df[col].dtype.name == 'category'):
                df[col].cat.set_categories(cat_dict[col], inplace=True)

        # if missing unique IDs occur in both features, remove them from dictionary
        if feature_list[0] in missing_dict and feature_list[1] in missing_dict:
            missing_match = [list(
                v) for v in missing_dict[feature_list[0]] if v in missing_dict[feature_list[1]]]
            for v in missing_match:
                missing_dict[feature_list[0]].remove(v)
                missing_dict[feature_list[1]].remove(v)
                print('\tOBJECTIDs {} to {} are missing from both feature classes. No need for dummy rows'.format(
                    min(v), max(v)))

        # insert dummy rows into dataframe(s) for missing unique IDs
        for x in range(2):
            if feature_list[x] in missing_dict and missing_dict[feature_list[x]] != []:
                for v in missing_dict[feature_list[x]]:
                    print('\tOBJECTIDs {} to {} are missing from {}. Adding dummy rows to facilitate comparison.'.format(
                        min(v), max(v), feature_list[x]))
                dummy_rows = [val for sublist in missing_dict[feature_list[x]]
                              for val in sublist]
                df_list[x] = df_list[x].reindex(
                    df_list[x].index.values.tolist()+dummy_rows)

        # if feature has a BAPID field, ensure it's called BAPID (simplifies things for later on)
        bapid = ''
        for col in df_list[0].columns:
            if col == 'BUSINESS_AREA_PROJECT_ID':
                df_list[0].rename(
                    {'BUSINESS_AREA_PROJECT_ID': 'BAPID'}, axis=1, inplace=True)
                df_list[1].rename(
                    {'BUSINESS_AREA_PROJECT_ID': 'BAPID'}, axis=1, inplace=True)
                bapid = 'BAPID'
            if col == 'BAPID':
                bapid = col
        
        # check if feature has BAPIDs (these will be compared by BAPID, rather than a row-wise comparison of entire dataframe)
        # begin by building lists of BAPIDs found in one feature and not the other
        if bapid in df_list[0].columns and bapid in df_list[1].columns:
            base_bapids = list(df_list[0][bapid].dropna().unique())
            test_bapids = list(df_list[1][bapid].dropna().unique())
            base_only_bapids = set(base_bapids).difference(set(test_bapids))
            test_only_bapids = set(test_bapids).difference(set(base_bapids))
            if len(base_bapids) != len(test_bapids):
                print('\tThere are {} BAPIDs in base feature.'.format(
                    len(base_bapids)))
                print('\tThere are {} BAPIDs in test feature.'.format(
                    len(test_bapids)))
            if base_only_bapids:
                print('\t{} BAPID(s) found only in base feature: {}'.format(len(base_only_bapids),
                                                                            sorted(base_only_bapids)))
            if test_only_bapids:
                print('\t{} BAPID(s) found only in test feature: {}'.format(len(test_only_bapids),
                                                                            sorted(test_only_bapids)))

            # group dataframes by BAPID
            base_g = df_list[0].groupby(bapid)
            base_groups = base_g.groups
            test_g = df_list[1].groupby(bapid)
            test_groups = test_g.groups

            # get individual BAPIDs as new dataframes, add to dictionary
            grouped_dfs = defaultdict(list)
            for k, v in base_groups.items():
                new = base_g.get_group(k).reset_index()
                new.name = 'BAPID_' + str(k)
                grouped_dfs[k].append(new)
            for k, v in test_groups.items():
                new = test_g.get_group(k).reset_index()
                new.name = 'BAPID_' + str(k)
                grouped_dfs[k].append(new)

            # if BAPID found in both features, run further comparison with dataframe_compare function
            processed_bapids = []
            for k, v in grouped_dfs.items():
                if len(v) == 2:
                    result = dataframe_compare(grouped_dfs[k])
                    if result is not None:
                        processed_bapids.extend(result)

            # handle the results of dataframe_compare - concatenate BAPID results into single dataframes
            if processed_bapids:
                dup_list = [
                    df for df in processed_bapids if '_test_dup' in df.name]
                if dup_list:
                    dup = pd.concat(dup_list)
                    dup.name = trunc_xlsx_sheet_name(feature_name + '_dup')
                    return_list.append(dup)
                cols_list = [
                    df for df in processed_bapids if '_cols' in df.name]
                if cols_list:
                    cols = pd.concat(cols_list)
                    cols = cols.groupby('all_vals_mismatched')[
                        'BAPID'].apply(', '.join).reset_index()
                    cols.name = trunc_xlsx_sheet_name(feature_name + '_cols')
                    return_list.append(cols)
                    print(
                        '\tDropped columns where all values are mismatched to facilitate comparison. See Excel report.')
                att_list = [df for df in processed_bapids if '_att' in df.name]
                if att_list:
                    att = pd.concat(att_list)
                    att.name = trunc_xlsx_sheet_name(feature_name + '_att')
                    return_list.append(att)
                else:
                    print('\tAttributes match.')

            if return_list:
                return return_list
            elif not return_list:
                return None

        # if features do not have BAPID field, ignore BAPID-specific tasks and proceed straight to dataframe_compare
        else:
            result = dataframe_compare(df_list)
            if result is not None:
                if not any('_att' in df.name for df in result):
                    print('\tAttributes match.')
                return result
            elif result is None:
                print('\tAttributes match.')
                return None

    except Exception as e:
        print('\tSomething went wrong setting up the attribute comparison for {}. \n\t{}. \n\tSkipping to next feature.'.format(
            feature_name, traceback.format_exc()))
        pass


def schema_compare(feature_list):
    """Given a list containing the paths of two identically named geodatabase features (ie. feature class, table), compare their schemas.
    Return findings in dataframe."
    \nParameters:
    \tfeature_list (list): list of paths. eg. [r'X:\TEIS_Env_Master\Operational_Data.gdb\TEIS_Master_Short_Tbl', r'X:\Deliverables\Operational_Data.gdb\TEIS_Master_Short_Tbl']
    \nReturns:
    \n\tdf (dataframe): dataframe"""

    def make_fields_dict(feature):

        fields = ap.ListFields(feature)
        fieldDict = {'headers': ['Alias', 'Type',
                                 'Length', 'Precision', 'Domain']}

        for f in fields:
            fieldDict[f.name] = [f.aliasName, f.type,
                                 f.length, f.precision, f.domain]

        return fieldDict

    base_dict = make_fields_dict(feature_list[0])
    test_dict = make_fields_dict(feature_list[1])

    if base_dict != test_dict:
        schema_dict = {'field': [], 'property': [], 'base_value': [],
                       'test_value': [], 'absent_in_base': [], 'absent_in_test': []}

        base_only = set(base_dict.keys()).difference(set(test_dict.keys()))
        test_only = set(test_dict.keys()).difference(set(base_dict.keys()))
        for k in (k for k in base_only if base_only):
            schema_dict['field'].append(k)
            schema_dict['property'].append(np.nan)
            schema_dict['base_value'].append(np.nan)
            schema_dict['test_value'].append(np.nan)
            schema_dict['absent_in_base'].append(np.nan)
            schema_dict['absent_in_test'].append('y')
        for k in (k for k in test_only if test_only):
            schema_dict['field'].append(k)
            schema_dict['property'].append(np.nan)
            schema_dict['base_value'].append(np.nan)
            schema_dict['test_value'].append(np.nan)
            schema_dict['absent_in_base'].append('y')
            schema_dict['absent_in_test'].append(np.nan)
        for k in (k for k in base_dict.keys() if k in test_dict.keys() and base_dict[k] != test_dict[k]):
            for i in (base_dict[k].index(x) for x in base_dict[k] if x not in test_dict[k] or base_dict[k].index(x) != test_dict[k].index(x)):
                # print('\t{} of {} field does not match. {} for base feature class and {} for test feature class'\
                # .format(base_dict['headers'][i], k, base_dict[k][i], test_dict[k][i]))
                schema_dict['field'].append(k)
                schema_dict['property'].append(base_dict['headers'][i])
                schema_dict['base_value'].append(base_dict[k][i])
                schema_dict['test_value'].append(test_dict[k][i])
                schema_dict['absent_in_base'].append(np.nan)
                schema_dict['absent_in_test'].append(np.nan)

        df = pd.DataFrame.from_dict(schema_dict)
        df.name = trunc_xlsx_sheet_name(os.path.basename(
            os.path.normpath(feature_list[0]))+'_sch')
        return df

    elif base_dict == test_dict:
        return None


def sr_compare(feature_list):
    """Given a list containing the paths of two identically named feature classes, compare their spatial references.
    Return findings in dataframe."
    \nParameters:
    \tfeature_list (list): list of paths. eg. [r'X:\TEIS_Env_Master\Operational_Data.gdb\TEIS_Master_Short_Tbl', r'X:\Deliverables\Operational_Data.gdb\TEIS_Master_Short_Tbl']
    \nReturns:
    \n\ttext, printed to console or log, stating whether spatial references match and what it/they is/are"""

    sr_list = []
    for fc in feature_list:
        sr = ap.Describe(fc).spatialReference
        sr_list.append(sr.name)

    if sr_list[0] == sr_list[1]:
        return print('\tSpatial references match. {} for both feature classes.'
                     .format(sr_list[0]))
    elif sr_list[0] != sr_list[1]:
        return print('\tSpatial references do not match. {} for {} and {} for {}'
                     .format(sr_list[0], feature_list[0], sr_list[1], feature_list[1]))


def compile_report(env_name, df_list, out_dir):
    """Export dataframes to separate sheets in an Excel workbook.
    \nParameters:
    \tenv_name (str): Name of environment (geodatabase) being evaluated. eg. 'Operational_Data'
    \tdf_list (list): list of dataframes to export
    \tout_dir (str): path of location to save Excel file"""

    writer = pd.ExcelWriter(os.path.join(
        out_dir, env_name + '_comparison_rpt.xlsx'), engine='xlsxwriter', date_format='YYYY-MM-DD')

    for df in df_list:
        df.to_excel(writer, sheet_name=df.name)

    writer.book.use_zip64()
    writer.save()
