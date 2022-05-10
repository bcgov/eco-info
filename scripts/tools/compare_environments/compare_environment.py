# ================================================================================================================
# Title: compare_environment.py
# Author: Conor MacNaughton (idir: cmacnaug)
# Date created: 2022/03/25
# Date updated:
# Description: For comparison/QA of two environments (directories). Finds distinct files/folders and modified
#              same-name items at same level of folder structure on both sides of comparison. Exports results to Excel.
#              Prompts user to select which same-name, same-level geodatabases they'd like to further compare
#              (calling compare_gdb.py).
# Python Version: 3.7
# ================================================================================================================

from filecmp import dircmp
import os
import pandas as pd
from collections import defaultdict
from compare_gdb import compare_gdb
from compare_feature import compile_report
from datetime import datetime as dt

print('\nDirectory comparison started at: ', dt.now())

# enter paths of directories to compare and an output location
path1 = r''
path2 = r''
output_loc = r''

# create dictionary of {folder name: list of paths terminating in folder name}
folder_dict = defaultdict(list)
for folder, sub_folder, files in os.walk(path1, topdown=False):
    folder_dict[os.path.basename(os.path.normpath(folder))].append(folder)
for folder, sub_folder, files in os.walk(path2, topdown=False):
    folder_dict[os.path.basename(os.path.normpath(folder))].append(folder)

# create dictionary of folders found on both sides of comparison
to_compare = {k: v for k, v in folder_dict.items() if len(v) == 2 and any(
    path1 in f for f in v) and any(path2 in f for f in v)}
to_compare['roots'] = [path1, path2]
# create dictionary of folder names that occur more than once on a side of the comparison
multi = {k: v for k, v in folder_dict.items() if len(v) > 2 and any(
    path1 in f for f in v) and any(path2 in f for f in v)}

# iterate through same-name folders, and add left-only, right-only, modified, and common items to relevant dictionaries
mod_files = defaultdict(list)
left_only = defaultdict(list)
right_only = defaultdict(list)
common_gdbs = []
df_list = []
for k, v in to_compare.items():
    if not k.endswith('.gdb'):
        dcmp = dircmp(v[0], v[1])
        for index, name in enumerate(dcmp.diff_files):
            mod_files[index] = [name, dcmp.left, dcmp.right]

        if dcmp.left_only:
            for i in dcmp.left_only:
                left_only[dcmp.left].append(i)

        if dcmp.right_only:
            for i in dcmp.right_only:
                right_only[dcmp.right].append(i)

        if dcmp.common:
            for i in (i for i in dcmp.common if i.endswith('.gdb')):
                common_gdbs.append(
                    [os.path.join(dcmp.left, i), os.path.join(dcmp.right, i)])

# remove items from common_gdbs if they occur more than once on a side of the comparison to decrease chance of spurious comparison
if multi:
    print("""\nSame-name items found at different levels of the directory. See Excel report file for details. 
    If necessary, you can compare these manually or, if they are geodatabases, using compare_gdb.py separately.""")
    if common_gdbs:
        for item in common_gdbs:
            for k, v in multi.items():
                for elem in (elem for elem in item if elem in v):
                    v.remove(elem)

# create dataframes from dictionaries and append to list
df_multi = pd.DataFrame.from_dict(multi, orient='index')
df_multi.index.name = 'item'
df_multi.columns = ['path_'+str(n+1) for n in range(len(df_multi.columns))]
df_multi.reset_index(inplace=True)
df_multi.index = df_multi.index + 1
df_multi.name = 'same_name_diff_level'
df_list.append(df_multi)
dfmf = pd.DataFrame.from_dict(mod_files, orient='index', columns=[
    'item_name', 'left_path', 'right_path'])
dfmf.index = dfmf.index + 1
dfmf.name = 'modified_files'
df_list.append(dfmf)
dflo = pd.DataFrame.from_dict(left_only, orient='index')
dflo.index.name = 'path'
dflo.columns = ['item_'+str(n+1) for n in range(len(dflo.columns))]
dflo.reset_index(inplace=True)
dflo.index = dflo.index + 1
dflo.name = 'left_only_items'
df_list.append(dflo)
dfro = pd.DataFrame.from_dict(right_only, orient='index')
dfro.index.name = 'path'
dfro.columns = ['item_'+str(n+1) for n in range(len(dfro.columns))]
dfro.reset_index(inplace=True)
dfro.index = dfro.index + 1
dfro.name = 'right_only_items'
df_list.append(dfro)

# export list of dataframes to Excel
if df_list:
    compile_report(os.path.basename(os.path.normpath(path1)),
                   df_list, output_loc)
    print('\nDirectory comparison Excel report exported to {}'.format(output_loc))

# print list of common geodatabases and prompt user to select which ones they'd like to compare, calling compare_gdb
if common_gdbs:
    print('\nSame-name geodatabases found at equivalent position in directory:')
    for index, gdb in enumerate(common_gdbs):
        print(index, gdb)
    gdb_indices = input(
        '\nEnter ALL or the index of each pair you would like to compare, separated by a space: ')
    if gdb_indices == 'ALL':
        to_keep = common_gdbs
    else:
        gdb_indices = list(int(num) for num in gdb_indices.strip().split())
        to_keep = [i for i in common_gdbs if common_gdbs.index(
            i) in gdb_indices]
    if to_keep:
        print('Comparing geodatabases...')
        for gdb in to_keep:
            compare_gdb(gdb, output_loc)
    else:
        print('No geodatabases to compare.')

sys.stdout = sys.__stdout__
print('\nDirectory comparison completed at: ', dt.now())
print(">>>> DONE >>>>")
