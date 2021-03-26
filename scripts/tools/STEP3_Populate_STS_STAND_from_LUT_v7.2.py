"""

Original Author:
Madrone (Jeff Kruys); 

Created on:
2017-05-23

Purpose:
This script populates the structrual stage and stand values in the TEM feature class from the data provided 
by the Lookup Table.

Usage:
STEP3_Populate_STS_STAND_from_LUT.py bfc ssl [-h] [-l] [-ld]

Positional Arguments:
   bfc              TEM feature class
   ssl              Structural Stage Look-Up Table CSV file
   
Optional Arguments:
  -h, --help       show this help message and exit
  -l, --level      log level messages to display; Default: 20 - INFO
  -ld, --log_dir   path to directory for output log file

Example Input:
X:\fullpath\STEP3_Populate_STS_STAND_from_LUT.py Y:\fullpath\bfc Z:\fullpath\vfc W:\fullpath\ss_lut.csv


History

2021-01-21 (JK): Script used for GBR - update age class values in vri_stand_class_dict (Madrone Dosier 20.0243)
2021-01-27 (AE): Script updated to use Best age field(AGE_CL_STS & STD) instead of VRI Age field (VR_AGE_CL_STS &STD)
2021-02-04 (JK): Updated to new script format style with logging; added code to use a new VRI field, STD_VRI, 
                 which would have been added to the TEM feature class after running a prior script. Removed section
                 of code that "overlays in" AGE_CL_STS/STD fields from VRI; this now takes place in a separate script.
                 This script now requires that AGE_CL_STS, AGE_CL_STD and STD_VRI are already present in the TEM.
2021-02-05 (AE): Updated the script to the New Coastal Age Bins
2021-02-08 (AE): Changed Ecounit to read SITE_S instead of SITE_MC 
2021-02-10 (JK): Rewrote logic to consider first the ecosystem unit with site series, then the ecosystem unit with
                 mapcode, when matching a TEM ecosystem unit with a unit in the LUT. Removed requirement of a TEIS_ID
                 field in the TEM (it was required when this script included performing an intersect with VRI). Added
                 code to check that other required fields exist in TEM. Added code to ignore subzone, variant and phase
                 in the TEM for BAFA, CMA and IMA zones which, in the LUT, will always be specified without subzone, 
                 variant and phase. Redid the logic for assigning STRCT_S# and STAND_A#. Revised logic to get rid of
                 instances in the original data where stand codes exist while STS is blank, and where STS/STD codes
                 that are out of range for the eco unit are not kept even when Use_Default_STS = Y.
2021-02-26 (AE): updated the script, took out 3 in (if row[cfd["STRCT_S{}".format(i)]] in ["3", "4", "5", "6", "7"]:)
"""

import logging
import time
import os
import sys
import ctypes
import csv
import operator

from argparse import ArgumentParser
from argparse import RawTextHelpFormatter

def main(tem_fc, sts_csv):
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

    req_tem_fields = ["BGC_ZONE", "BGC_SUBZON", "BGC_VRT", "BGC_PHASE", "SDEC_1", "SDEC_2", "SDEC_3", "SITE_S1", 
                      "SITE_S2", "SITE_S3", "SITEMC_S1", "SITEMC_S2", "SITEMC_S3", "STRCT_S1", "STRCT_S2", "STRCT_S3", 
                      "STAND_A1", "STAND_A2", "STAND_A3", "AGE_CL_STS", "AGE_CL_STD", "STD_VRI"]
    existing_tem_fields = [f.name for f in arcpy.ListFields(tem_fc)]
    missing_fields = []
    for req_tem_field in req_tem_fields:
        if req_tem_field not in existing_tem_fields:
            missing_fields.append(req_tem_field)
    if len(missing_fields) > 0:
        logging.error("**** Specified TEM feature class is missing required fields: {}. Exiting script.".format(
                str(missing_fields)))
        sys.exit()

    if not os.path.isfile(sts_csv):
        logging.error("**** Specified STS LUT CSV file {} does not exist. Exiting script.".format(sts_csv))
        sys.exit()

    req_csv_fields = ["BGC_Label", "BGC_ZONE", "BGC_SUBZON", "BGC_VRT", "BGC_PHASE", "SITE_S", "SITEMC_S", 
                           "REALM", "GROUP", "CLASS", "KIND", "Forested", "Default_Orig_STS", "Apply_STS", "STS_Range", 
                           "STS_Climax", "SComp_Climax", "SComp_Age_1-15", "SComp_Age_16-30", "SComp_Age_31-50", 
                           "SComp_Age_51-80", "SComp_Age_>80", "STS_Age_0-2", "STS_Age_3-5", "STS_Age_6-10", 
                           "STS_Age_11-20", "STS_Age_21-40", "STS_Age_41-60", "STS_Age_61-80", "STS_Age_81-100", 
                           "STS_Age_101-120", "STS_Age_121-140", "STS_Age_141-180", "STS_Age_181-200", 
                           "STS_Age_201-250", "STS_Age_251-399", "STS_Age_400+", "Snow_Code"]

    sts_csv_obj = open(sts_csv, "rU")
    csvReader = csv.DictReader(sts_csv_obj)
    missing_fields = []
    csv_line_total = 0
    for data in csvReader:
        csv_line_total += 1
    for req_field in req_csv_fields:
        if req_field not in data.keys():
            missing_fields.append(req_field)
    if len(missing_fields) > 0:
        logging.error("*** Structural stage lookup table missing required field(s): {}".format(str(missing_fields)))
        sys.exit()
    del csvReader
    sts_csv_obj.close()

    # ---------------------------------------------------------------------------------------------------------
    # Read the structural stage lookup table into dictionaries
    # ---------------------------------------------------------------------------------------------------------

    logging.info("Reading STS lookup table")

    forested_ss_dict = {}
    use_original_sts_ss_dict = {}
    apply_sts_ss_dict = {}
    sts_range_ss_dict = {}
    stand_climax_ss_dict = {}
    sts_climax_ss_dict = {}
    sts_age_lookup_ss_dict = {}
    stand_age_lookup_ss_dict = {}
    forested_mc_dict = {}
    use_original_sts_mc_dict = {}
    apply_sts_mc_dict = {}
    sts_range_mc_dict = {}
    stand_climax_mc_dict = {}
    sts_climax_mc_dict = {}
    sts_age_lookup_mc_dict = {}
    stand_age_lookup_mc_dict = {}
    line_counter = 0
    sts_csv_obj = open(sts_csv, "rU")
    csvReader = csv.DictReader(sts_csv_obj)
    for data in csvReader:
        line_counter += 1
        curr_bgc_zone          = str(data["BGC_ZONE"]).replace('"','').replace(' ','')
        curr_bgc_subzon        = str(data["BGC_SUBZON"]).replace('"','').replace(' ','')
        curr_bgc_vrt           = str(data["BGC_VRT"]).replace('"','').replace('0','')
        curr_bgc_phase         = str(data["BGC_PHASE"]).replace('"','').replace(' ','')
        curr_beu_ss            = str(data["SITE_S"]).replace('"','').replace(' ','')
        curr_beu_mc            = str(data["SITEMC_S"]).replace('"','').replace(' ','')
        curr_forested          = str(data["Forested"]).replace('"','').replace(' ','')
        curr_default_orig_sts  = str(data["Default_Orig_STS"]).replace('"','').replace(' ','')
        curr_apply_sts         = str(data["Apply_STS"]).replace('"','').replace(' ','')
        curr_sts_range         = str(data["STS_Range"]).replace('"','').replace(' ','')
        curr_sts_climax        = str(data["STS_Climax"]).replace('"','').replace(' ','')
        curr_stand_climax      = str(data["SComp_Climax"]).replace('"','').replace(' ','')
        curr_STAND_Age_0_15    = str(data["SComp_Age_1-15"]).replace('"','').replace(' ','')
        curr_STAND_Age_16_30   = str(data["SComp_Age_16-30"]).replace('"','').replace(' ','')
        curr_STAND_Age_31_50   = str(data["SComp_Age_31-50"]).replace('"','').replace(' ','')
        curr_STAND_Age_51_80   = str(data["SComp_Age_51-80"]).replace('"','').replace(' ','')
        curr_STAND_Age_81_9999 = str(data["SComp_Age_>80"]).replace('"','').replace(' ','')
        curr_STS_Age_0_2       = str(data["STS_Age_0-2"]).replace('"','').replace(' ','')
        curr_STS_Age_3_5       = str(data["STS_Age_3-5"]).replace('"','').replace(' ','')
        curr_STS_Age_6_10      = str(data["STS_Age_6-10"]).replace('"','').replace(' ','')
        curr_STS_Age_11_20     = str(data["STS_Age_11-20"]).replace('"','').replace(' ','')
        curr_STS_Age_21_40     = str(data["STS_Age_21-40"]).replace('"','').replace(' ','')    
        curr_STS_Age_41_60     = str(data["STS_Age_41-60"]).replace('"','').replace(' ','')
        curr_STS_Age_61_80     = str(data["STS_Age_61-80"]).replace('"','').replace(' ','')
        curr_STS_Age_81_100    = str(data["STS_Age_81-100"]).replace('"','').replace(' ','')          
        curr_STS_Age_101_120   = str(data["STS_Age_101-120"]).replace('"','').replace(' ','')          
        curr_STS_Age_121_140   = str(data["STS_Age_121-140"]).replace('"','').replace(' ','')
        curr_STS_Age_141_180   = str(data["STS_Age_141-180"]).replace('"','').replace(' ','')
        curr_STS_Age_181_200   = str(data["STS_Age_181-200"]).replace('"','').replace(' ','')
        curr_STS_Age_201_250   = str(data["STS_Age_201-250"]).replace('"','').replace(' ','')
        curr_STS_Age_251_399   = str(data["STS_Age_251-399"]).replace('"','').replace(' ','')  
        curr_STS_Age_400_9999  = str(data["STS_Age_400+"]).replace('"','').replace(' ','')          

        curr_bgc_unit = curr_bgc_zone + curr_bgc_subzon + curr_bgc_vrt + curr_bgc_phase

        if curr_beu_ss != "":
            curr_eco_unit_ss = curr_bgc_unit + "~" + curr_beu_ss

            sts_age_lookup_ss_dict[curr_eco_unit_ss] = {}
            sts_age_lookup_ss_dict[curr_eco_unit_ss][2] = curr_STS_Age_0_2
            sts_age_lookup_ss_dict[curr_eco_unit_ss][5] = curr_STS_Age_3_5  
            sts_age_lookup_ss_dict[curr_eco_unit_ss][10] = curr_STS_Age_6_10
            sts_age_lookup_ss_dict[curr_eco_unit_ss][20] = curr_STS_Age_11_20
            sts_age_lookup_ss_dict[curr_eco_unit_ss][40] = curr_STS_Age_21_40
            sts_age_lookup_ss_dict[curr_eco_unit_ss][60] = curr_STS_Age_41_60
            sts_age_lookup_ss_dict[curr_eco_unit_ss][80] = curr_STS_Age_61_80
            sts_age_lookup_ss_dict[curr_eco_unit_ss][100] = curr_STS_Age_81_100
            sts_age_lookup_ss_dict[curr_eco_unit_ss][120] = curr_STS_Age_101_120  
            sts_age_lookup_ss_dict[curr_eco_unit_ss][140] = curr_STS_Age_121_140
            sts_age_lookup_ss_dict[curr_eco_unit_ss][180] = curr_STS_Age_141_180  
            sts_age_lookup_ss_dict[curr_eco_unit_ss][200] = curr_STS_Age_181_200
            sts_age_lookup_ss_dict[curr_eco_unit_ss][250] = curr_STS_Age_201_250
            sts_age_lookup_ss_dict[curr_eco_unit_ss][399] = curr_STS_Age_251_399   
            sts_age_lookup_ss_dict[curr_eco_unit_ss][9999] = curr_STS_Age_400_9999

            stand_age_lookup_ss_dict[curr_eco_unit_ss] = {}
            stand_age_lookup_ss_dict[curr_eco_unit_ss][15] = curr_STAND_Age_0_15
            stand_age_lookup_ss_dict[curr_eco_unit_ss][30] = curr_STAND_Age_16_30
            stand_age_lookup_ss_dict[curr_eco_unit_ss][50] = curr_STAND_Age_31_50
            stand_age_lookup_ss_dict[curr_eco_unit_ss][80] = curr_STAND_Age_51_80
            stand_age_lookup_ss_dict[curr_eco_unit_ss][9999] = curr_STAND_Age_81_9999
                    
            sts_range_ss_dict[curr_eco_unit_ss] = curr_sts_range.split(",")
            sts_climax_ss_dict[curr_eco_unit_ss] = curr_sts_climax
            stand_climax_ss_dict[curr_eco_unit_ss] = curr_stand_climax
            forested_ss_dict[curr_eco_unit_ss] = curr_forested
            use_original_sts_ss_dict[curr_eco_unit_ss] = curr_default_orig_sts
            apply_sts_ss_dict[curr_eco_unit_ss] = curr_apply_sts

        if curr_beu_mc != "":
            curr_eco_unit_mc = curr_bgc_unit + "~" + curr_beu_mc

            sts_age_lookup_mc_dict[curr_eco_unit_mc] = {}
            sts_age_lookup_mc_dict[curr_eco_unit_mc][2] = curr_STS_Age_0_2
            sts_age_lookup_mc_dict[curr_eco_unit_mc][5] = curr_STS_Age_3_5  
            sts_age_lookup_mc_dict[curr_eco_unit_mc][10] = curr_STS_Age_6_10
            sts_age_lookup_mc_dict[curr_eco_unit_mc][20] = curr_STS_Age_11_20
            sts_age_lookup_mc_dict[curr_eco_unit_mc][40] = curr_STS_Age_21_40
            sts_age_lookup_mc_dict[curr_eco_unit_mc][60] = curr_STS_Age_41_60
            sts_age_lookup_mc_dict[curr_eco_unit_mc][80] = curr_STS_Age_61_80
            sts_age_lookup_mc_dict[curr_eco_unit_mc][100] = curr_STS_Age_81_100
            sts_age_lookup_mc_dict[curr_eco_unit_mc][120] = curr_STS_Age_101_120  
            sts_age_lookup_mc_dict[curr_eco_unit_mc][140] = curr_STS_Age_121_140
            sts_age_lookup_mc_dict[curr_eco_unit_mc][180] = curr_STS_Age_141_180  
            sts_age_lookup_mc_dict[curr_eco_unit_mc][200] = curr_STS_Age_181_200
            sts_age_lookup_mc_dict[curr_eco_unit_mc][250] = curr_STS_Age_201_250
            sts_age_lookup_mc_dict[curr_eco_unit_mc][399] = curr_STS_Age_251_399   
            sts_age_lookup_mc_dict[curr_eco_unit_mc][9999] = curr_STS_Age_400_9999

            stand_age_lookup_mc_dict[curr_eco_unit_mc] = {}
            stand_age_lookup_mc_dict[curr_eco_unit_mc][15] = curr_STAND_Age_0_15
            stand_age_lookup_mc_dict[curr_eco_unit_mc][30] = curr_STAND_Age_16_30
            stand_age_lookup_mc_dict[curr_eco_unit_mc][50] = curr_STAND_Age_31_50
            stand_age_lookup_mc_dict[curr_eco_unit_mc][80] = curr_STAND_Age_51_80
            stand_age_lookup_mc_dict[curr_eco_unit_mc][9999] = curr_STAND_Age_81_9999
                    
            sts_range_mc_dict[curr_eco_unit_mc] = curr_sts_range.split(",")
            sts_climax_mc_dict[curr_eco_unit_mc] = curr_sts_climax
            stand_climax_mc_dict[curr_eco_unit_mc] = curr_stand_climax
            forested_mc_dict[curr_eco_unit_mc] = curr_forested
            use_original_sts_mc_dict[curr_eco_unit_mc] = curr_default_orig_sts
            apply_sts_mc_dict[curr_eco_unit_mc] = curr_apply_sts

        if line_counter == 100 or line_counter % 1000 == 0 or line_counter == csv_line_total:
            logging.info("    Read {} of {} lines".format(line_counter, csv_line_total))

    # ---------------------------------------------------------------------------------------------------------
    # Add new fields if necessary, FORESTED_# and STS_Com 
    # ---------------------------------------------------------------------------------------------------------

    tem_fields = [f.name for f in arcpy.ListFields(tem_fc)]

    for i in range(1, 4):
        new_field = "FORESTED_{}".format(i)
        if new_field not in tem_fields:
            logging.info("Adding {} field to TEM".format(new_field))
            arcpy.AddField_management(tem_fc, new_field, "TEXT", "#", "#", "1")

    new_field = "STS_Comment"
    if new_field not in tem_fields:
        logging.info("Adding {} field to TEM".format(new_field))
        arcpy.AddField_management(tem_fc, new_field, "TEXT", "#", "#", "1000")

    logging.info("Updating attribute values in TEM polygons")
    row_count = 0
    cursor_fields = ["BGC_ZONE", "BGC_SUBZON", "BGC_VRT", "BGC_PHASE", "SDEC_1", "SDEC_2", "SDEC_3", "SITE_S1", 
                     "SITE_S2", "SITE_S3", "SITEMC_S1", "SITEMC_S2", "SITEMC_S3", "STRCT_S1", "STRCT_S2", "STRCT_S3", 
                     "STAND_A1", "STAND_A2", "STAND_A3", "AGE_CL_STS", "AGE_CL_STD", "STD_VRI", "FORESTED_1", 
                     "FORESTED_2", "FORESTED_3", "STS_Comment"]
                  
    cfd = {}
    for cursor_field in cursor_fields:
        cfd[cursor_field] = cursor_fields.index(cursor_field)
    row_total = int(arcpy.GetCount_management(tem_fc).getOutput(0))
    with arcpy.da.UpdateCursor(tem_fc, cursor_fields) as cursor:
        for row in cursor:
            row_count += 1
            
            # New logic:
            # If the eco unit (first consider the site series, then the mapcode) is found in the LUT:
            #     Assign the "Forested" value in the LUT to the FORESTED_# field
            #     If the "Use Default STS" value in the LUT is "Y" and existing STRCT_S# is not blank and existing 
            #                     STRCT_S# is in the unit's range:
            #         Keep the existing value in STRCT_S# 
            #         If STRCT_S# starts with 4, 5, 6 or 7:
            #             If STD_VRI is B, C or M:
            #                 Assign the value in STD_VRI to STAND_A#
            #             If STD_VRI is blank:
            #                 Keep the existing value in STAND_A#
            #         If STRCT_S# does not start with 4, 5, 6 or 7:
            #             Keep the existing value in STAND_A#
            #     If the "Use Default STS" value in the LUT is "N" or existing STRCT_S# is blank or existing STRCT_S# 
            #                     is not in the unit's range:
            #         If AGE_CL_STS > 0:
            #             Assign the looked up STS value from the LUT to STRCT_S#
            #             If the newly-assigned STRCT_S# starts with 4, 5, 6 or 7:
            #                 If STD_VRI is B, C or M:
            #                     Assign the STD_VRI value to STAND_A#
            #                 If STD_VRI is blank:
            #                     Assign the looked up STD value from the LUT to STAND_A#
            #             If STRCT_S# doesn't start with 4, 5, 6 or 7:
            #                 Assign the looked up STD value from the LUT to STAND_A#  
            #         If AGE_CL_STS = -1:
            #             If the "Apply STS" value in the LUT is "Y":
            #                 Assign the climax STS value from the LUT to STRCT_S#
            #                 If STD_VRI is B, C or M and FORESTED_# = Y:
            #                     Assign the STD_VRI value to STAND_A#
            #                 If STD_VRI is blank or FORESTED_# = N:
            #                     Assign the climax STD value from the LUT to STAND_A#
            #             If the "Apply STS" value in the LUT is "N":
            #                 Assign a blank to STRCT_S#
            #                 Assign a blank to STAND_A#
            # If neither of the eco units (with site series or with mapcode) is found in the LUT:
            #     Assign blanks to FORESTED_#, STRCT_S# and STAND_A#.

            sts_com = ""
            if row[cfd["AGE_CL_STS"]] != None:
                for i in range(1, 4):
                    if row[cfd["SDEC_{}".format(i)]] in range(1, 11):
                        eco_unit_ss = str(row[cfd["BGC_ZONE"]]).replace("None", "") 
                        if eco_unit_ss not in ["BAFA", "CMA", "IMA"]:
                            # If BGC_ZONE is BAFA, CMA or IMA, then disregard the subzone, variant and phase in the TEM,
                            # because for BAFA, CMA and IMA, the LUT only specifies zone, not subzone, variant or phase.
                            eco_unit_ss += str(row[cfd["BGC_SUBZON"]]).replace("None", "") 
                            eco_unit_ss += str(row[cfd["BGC_VRT"]]).replace("None", "").replace("0", "") 
                            eco_unit_ss += str(row[cfd["BGC_PHASE"]]).replace("None", "") + "~"
                        else:
                            eco_unit_ss += "~"
                        eco_unit_ss += str(row[cfd["SITE_S{}".format(i)]]).replace("None", "")

                        eco_unit_mc = str(row[cfd["BGC_ZONE"]]).replace("None", "") 
                        if eco_unit_mc not in ["BAFA", "CMA", "IMA"]:
                            # If BGC_ZONE is BAFA, CMA or IMA, then disregard the subzone, variant and phase in the TEM, 
                            # because for BAFA, CMA and IMA, the LUT only specifies zone, not subzone, variant or phase.
                            eco_unit_mc += str(row[cfd["BGC_SUBZON"]]).replace("None", "") 
                            eco_unit_mc += str(row[cfd["BGC_VRT"]]).replace("None", "").replace("0", "") 
                            eco_unit_mc += str(row[cfd["BGC_PHASE"]]).replace("None", "") + "~"
                        else:
                            eco_unit_mc += "~"
                        eco_unit_mc += str(row[cfd["SITEMC_S{}".format(i)]]).replace("None", "")

                        sts_was = row[cfd["STRCT_S{}".format(i)]]
                        std_was = row[cfd["STAND_A{}".format(i)]]

                        if eco_unit_ss in sts_age_lookup_ss_dict:
                            try:
                                forested = forested_ss_dict[eco_unit_ss]
                            except:
                                forested = ""
                            row[cfd["FORESTED_{}".format(i)]] = forested
                            sts_com += "Eco Unit (SS) {}: {}, ".format(i, eco_unit_ss)
                            sts_com += "For='{}' UseDefSTS='{}' ApplySTS='{}' Age={} ".format(forested, 
                                    use_original_sts_ss_dict[eco_unit_ss], apply_sts_ss_dict[eco_unit_ss], 
                                    row[cfd["AGE_CL_STS"]])
                            sts_com += "STD_VRI={} ".format(row[cfd["STD_VRI"]])
                            if use_original_sts_ss_dict[eco_unit_ss] == "Y" and row[cfd["STRCT_S{}".format(
                                        i)]] != "" and row[cfd["STRCT_S{}".format(i)]] in sts_range_ss_dict[
                                        eco_unit_ss]:
                                sts_com += "STRCT_S{} kept as '{}', ".format(i, row[cfd["STRCT_S{}".format(i)]])
                                if row[cfd["STRCT_S{}".format(i)]] in ["4", "5", "6", "7"]:
                                    if row[cfd["STD_VRI"]] in ["C", "B", "M"]:
                                        row[cfd["STAND_A{}".format(i)]] = row[cfd["STD_VRI"]]
                                        sts_com += "STAND_A{} was '{}', now '{}' (from STD_VRI), ".format(i, 
                                                std_was, row[cfd["STD_VRI"]])
                                    else:
                                        sts_com += "STAND_A{} kept as '{}', ".format(i, row[cfd["STAND_A{}".format(i)]])
                                else:                                        
                                    sts_com += "STAND_A{} kept as '{}', ".format(i, row[cfd["STAND_A{}".format(i)]])
                            else:
                                if not row[cfd["STRCT_S{}".format(i)]] in sts_range_ss_dict[eco_unit_ss] and row[cfd[
                                        "STRCT_S{}".format(i)]] != '':
                                    oor_msg = " (out of range)"
                                else:
                                    oor_msg = ""
                                if row[cfd["AGE_CL_STS"]] > 0:
                                    row[cfd["STRCT_S{}".format(i)]] = sts_age_lookup_ss_dict[eco_unit_ss][
                                            row[cfd["AGE_CL_STS"]]]
                                    sts_com += "STRCT_S{} was '{}'{}, now '{}' (from LUT), ".format(i, sts_was,
                                            oor_msg, row[cfd["STRCT_S{}".format(i)]])
                                    if row[cfd["STRCT_S{}".format(i)]][:1] in ["4", "5", "6", "7"]:
                                        if row[cfd["STD_VRI"]] in ["C", "B", "M"]:
                                            row[cfd["STAND_A{}".format(i)]] = row[cfd["STD_VRI"]]
                                            sts_com += "STAND_A{} was '{}', now '{}' (from STD_VRI), ".format(i, 
                                                    std_was, row[cfd["STD_VRI"]])
                                        else:
                                            row[cfd["STAND_A{}".format(i)]] = stand_age_lookup_ss_dict[eco_unit_ss][
                                                    row[cfd["AGE_CL_STD"]]]
                                            sts_com += "STAND_A{} was '{}', now '{}' (from LUT), ".format(i, std_was, 
                                                    row[cfd["STAND_A{}".format(i)]])
                                    else:
                                        row[cfd["STAND_A{}".format(i)]] = stand_age_lookup_ss_dict[eco_unit_ss][
                                                row[cfd["AGE_CL_STD"]]]
                                        sts_com += "STAND_A{} was '{}', now '{}' (from LUT), ".format(i, std_was, 
                                                row[cfd["STAND_A{}".format(i)]])
                                else:
                                    if apply_sts_ss_dict[eco_unit_ss] == "Y":
                                        row[cfd["STRCT_S{}".format(i)]] = sts_climax_ss_dict[eco_unit_ss]
                                        sts_com += "STRCT_S{} was '{}'{}, now '{}' (climax), ".format(i, sts_was, 
                                                oor_msg, row[cfd["STRCT_S{}".format(i)]])
                                        if row[cfd["STD_VRI"]] in ["C", "B", "M"] and forested == "Y":
                                            row[cfd["STAND_A{}".format(i)]] = row[cfd["STD_VRI"]]
                                            sts_com += "STAND_A{} was '{}', now '{}' (from STD_VRI), ".format(i, 
                                                    sts_was, row[cfd["STD_VRI"]])
                                        else:
                                            row[cfd["STAND_A{}".format(i)]] = stand_climax_ss_dict[eco_unit_ss]
                                            sts_com += "STAND_A{} was '{}', now '{}' (climax), ".format(i, std_was, 
                                                    row[cfd["STAND_A{}".format(i)]])
                                    else:
                                        row[cfd["STRCT_S{}".format(i)]] = ""
                                        row[cfd["STAND_A{}".format(i)]] = ""
                                        sts_com += "STRCT_S{} was '{}'{}, and STAND_A{} was '{}', ".format(i, sts_was, 
                                                oor_msg, i, std_was)
                                        sts_com += "now both blank (no age, and ApplySTS='N'), "
                        # If the eco unit with site series wasn't in the LUT, check the eco unit with the mapcode
                        elif eco_unit_mc in sts_age_lookup_mc_dict:
                            try:
                                forested = forested_mc_dict[eco_unit_mc]
                            except:
                                forested = ""
                            row[cfd["FORESTED_{}".format(i)]] = forested
                            sts_com += "Eco Unit (MC) {}: {}, ".format(i, eco_unit_mc)
                            sts_com += "For='{}' UseDefSTS='{}' ApplySTS='{}' Age={} ".format(forested, 
                                    use_original_sts_mc_dict[eco_unit_mc], apply_sts_mc_dict[eco_unit_mc], 
                                    row[cfd["AGE_CL_STS"]])
                            sts_com += "STD_VRI={} ".format(row[cfd["STD_VRI"]])
                            if use_original_sts_mc_dict[eco_unit_mc] == "Y" and row[cfd["STRCT_S{}".format(
                                        i)]] != "" and row[cfd["STRCT_S{}".format(i)]] in sts_range_mc_dict[
                                        eco_unit_mc]:
                                sts_com += "STRCT_S{} kept as '{}', ".format(i, row[cfd["STRCT_S{}".format(i)]])
                                if row[cfd["STRCT_S{}".format(i)]] in ["4", "5", "6", "7"]:
                                    if row[cfd["STD_VRI"]] in ["C", "B", "M"]:
                                        row[cfd["STAND_A{}".format(i)]] = row[cfd["STD_VRI"]]
                                        sts_com += "STAND_A{} was '{}', now '{}' (from STD_VRI), ".format(i, 
                                                std_was, row[cfd["STD_VRI"]])
                                    else:
                                        sts_com += "STAND_A{} kept as '{}', ".format(i, row[cfd["STAND_A{}".format(i)]])
                                else:                                        
                                    sts_com += "STAND_A{} kept as '{}', ".format(i, row[cfd["STAND_A{}".format(i)]])
                            else:
                                if not row[cfd["STRCT_S{}".format(i)]] in sts_range_mc_dict[eco_unit_mc] and row[cfd[
                                        "STRCT_S{}".format(i)]] != '':
                                    oor_msg = " (out of range)"
                                else:
                                    oor_msg = ""
                                if row[cfd["AGE_CL_STS"]] > 0:
                                    row[cfd["STRCT_S{}".format(i)]] = sts_age_lookup_mc_dict[eco_unit_mc][
                                            row[cfd["AGE_CL_STS"]]]
                                    sts_com += "STRCT_S{} was '{}'{}, now '{}' (from LUT), ".format(i, sts_was,
                                            oor_msg, row[cfd["STRCT_S{}".format(i)]])
                                    if row[cfd["STRCT_S{}".format(i)]][:1] in ["4", "5", "6", "7"]:
                                        if row[cfd["STD_VRI"]] in ["C", "B", "M"]:
                                            row[cfd["STAND_A{}".format(i)]] = row[cfd["STD_VRI"]]
                                            sts_com += "STAND_A{} was '{}', now '{}' (from STD_VRI), ".format(i, 
                                                    std_was, row[cfd["STD_VRI"]])
                                        else:
                                            row[cfd["STAND_A{}".format(i)]] = stand_age_lookup_mc_dict[eco_unit_mc][
                                                    row[cfd["AGE_CL_STD"]]]
                                            sts_com += "STAND_A{} was '{}', now '{}' (from LUT), ".format(i, std_was, 
                                                    row[cfd["STAND_A{}".format(i)]])
                                    else:
                                        row[cfd["STAND_A{}".format(i)]] = stand_age_lookup_mc_dict[eco_unit_mc][
                                                row[cfd["AGE_CL_STD"]]]
                                        sts_com += "STAND_A{} was '{}', now '{}' (from LUT), ".format(i, std_was, 
                                                row[cfd["STAND_A{}".format(i)]])
                                else:
                                    if apply_sts_mc_dict[eco_unit_mc] == "Y":
                                        row[cfd["STRCT_S{}".format(i)]] = sts_climax_mc_dict[eco_unit_mc]
                                        sts_com += "STRCT_S{} was '{}'{}, now '{}' (climax), ".format(i, sts_was, 
                                                oor_msg, row[cfd["STRCT_S{}".format(i)]])
                                        if row[cfd["STD_VRI"]] in ["C", "B", "M"] and forested == "Y":
                                            row[cfd["STAND_A{}".format(i)]] = row[cfd["STD_VRI"]]
                                            sts_com += "STAND_A{} was '{}', now '{}' (from STD_VRI), ".format(i, 
                                                    sts_was, row[cfd["STD_VRI"]])
                                        else:
                                            row[cfd["STAND_A{}".format(i)]] = stand_climax_mc_dict[eco_unit_mc]
                                            sts_com += "STAND_A{} was '{}', now '{}' (climax), ".format(i, std_was, 
                                                    row[cfd["STAND_A{}".format(i)]])
                                    else:
                                        row[cfd["STRCT_S{}".format(i)]] = ""
                                        row[cfd["STAND_A{}".format(i)]] = ""
                                        sts_com += "STRCT_S{} was '{}'{}, and STAND_A{} was '{}', ".format(i, sts_was, 
                                                oor_msg, i, std_was)
                                        sts_com += "now both blank (no age, and ApplySTS='N'), "
                        else:
                            row[cfd["STRCT_S{}".format(i)]] = ""
                            row[cfd["STAND_A{}".format(i)]] = ""
                            row[cfd["FORESTED_{}".format(i)]] = ""
                            sts_com += "Eco Unit {}: {}/{}, STRCT_S{} was '{}', STAND_A{} was '{}', ".format(i, 
                                    eco_unit_ss, eco_unit_mc, i, sts_was, i, std_was)
                            sts_com += "now both blank (eco units not found in LUT), "
            else:
                for i in range(1, 4):
                    sts_was = row[cfd["STRCT_S{}".format(i)]]
                    std_was = row[cfd["STAND_A{}".format(i)]]
                    row[cfd["STRCT_S{}".format(i)]] = ""
                    row[cfd["STAND_A{}".format(i)]] = ""
                    sts_com += "STRCT_S{} was '{}', STAND_A{} was '{}', ".format(i, sts_was, i, std_was)
                sts_com += "now all blank (AGE_CL_STS=Null)"

            sts_com = sts_com.rstrip(", ")

            row[cfd["STS_Comment"]] = sts_com

            try:
                cursor.updateRow(row)
            except:
                logging.error("Count not write row {}: {}".format(row_count, row))
                sys.exit()

            if row_count % 100000 == 0 or row_count == row_total:
                logging.info("    Processed {} of {} rows".format(row_count, row_total))

    # ---------------------------------------------------------------------------------------------------------
    # Done
    # ---------------------------------------------------------------------------------------------------------

    dtCalcNow = time.time()
    dtCalcScriptElapsed = dtCalcNow - dtCalcScriptStart
    logging.info("Script complete after " + SanitizeElapsedTime(dtCalcScriptElapsed))

if __name__ == '__main__':
    try:
        # Parse arguments
        parser = ArgumentParser(description='This script updates STS and Stand fields in a TEM feature class '
                                            'based on the AGE_CL_STS/STD fields, STD_VRI field, and the STS LUT.',
                                formatter_class=RawTextHelpFormatter)
        parser.add_argument('bfc', help='TEM feature class')
        parser.add_argument('ssl', help='Structural Stage Look-Up Table CSV file')
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
        main(args.bfc, args.ssl)

    except Exception as e:
        logging.exception('Unexpected exception. Program terminating.')
else:
    import arcpy
