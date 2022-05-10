# compare_environments


OVERVIEW

These tools are meant to provide the option of a "holistic" comparison of two versions of TEI environments (directories) - providing a shallow comparison of files and folders within two directories and a more in-depth comparison of geodatabases and their constituents. An example use-case is the delivery of a new TEIS environment. It can be compared to a previous version of the TEIS environment to catch any unexpected omissions or differences in spatial reference, schema, and attribute values and check if the expected new BAPIDs were loaded.

Using compare_environments.py, the user can launch the comparison and choose which same-name geodatabases they'd like to further assess. This script calls compare_gdb.py, which in turn calls functions from the compare_feature.py module.

compare_gdb.py can be used separately when a full environment comparison is not required, as can the functions contained in the compare_feature.py module.

Findings are logged and tabular results are exported to Excel.


INPUT PARAMETERS

1. Path of 'base' environment
2. Path of 'test' environment
3. Path of output location
* compare_gdb.py has a list of feature class and/or table names to ignore during comparison that the user may wish to alter


CONSIDERATIONS

1. Fields read in as 'BUSINESS_AREA_PROJECT_IDENTIFIER' are output as 'BAPID' in the log file and/or Excel.
2. Fields read in as 'PROJECT_POLYGON_IDENTIFIER' are output as 'PROJPOLYID' in the log file and/or Excel.
3. Fields where all values are mismatched are dropped to simplify further comparison. It is important to have a look at the Excel sheet showing which fields were dropped, and not just the sheet showing particular attribute mismatches. The log will indicate when fields are dropped.
4. When multiple identically named geodatabases are found on one side of the comparison a list of their paths is output to Excel and the user will have to manually choose which to run through compare_gdb.py and do these comparisons separately.
5. At present, certain qualities (such as duplicates) are only assessed for the test environment. It is important to make sure you input the environment paths in the correct order.
