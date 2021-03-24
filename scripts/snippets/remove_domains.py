# -*- coding: utf-8 -*-
"""
Created on Tue Mar 23 13:03:16 2021

@author: BAUGER
"""

fieldslist = [u'TDEC_1', u'PRTFLG_1', u'TTEX_1C', u'TTEX_1B', u'TTEX_1A', u'SURFM_1', u'SURFM_Q1', u'SURFM_ST1', u'SURF_E1A', u'SURF_E1B', u'SURF_E1C', u'BEDROCK_1', u'STTEX_1C', u'STTEX_1B', u'STTEX_1A', u'SSURFM_1', u'SSURFM_Q1', u'SSURFM_ST1', u'SSURF_E1A', u'SSURF_E1B', u'SSURF_E1C', u'TTTEX_1C', u'TTTEX_1B', u'TTTEX_1A', u'TSURFM_1', u'TSURFM_Q1', u'TSURFM_ST1', u'TSURF_E1A', u'TSURF_E1B', u'TSURF_E1C', u'COMREL1_2', u'TDEC_2', u'PRTFLG_2', u'TTEX_2C', u'TTEX_2B', u'TTEX_2A', u'SURFM_2', u'SURFM_Q2', u'SURFM_ST2', u'SURF_E2A', u'SURF_E2B', u'SURF_E2C', u'BEDROCK_2', u'STTEX_2C', u'STTEX_2B', u'STTEX_2A', u'SSURFM_2', u'SSURFM_Q2', u'SSURFM_ST2', u'SSURF_E2A', u'SSURF_E2B', u'SSURF_E2C', u'TTTEX_2C', u'TTTEX_2B', u'TTTEX_2A', u'TSURFM_2', u'TSURFM_Q2', u'TSURFM_ST2', u'TSURF_E2A', u'TSURF_E2B', u'TSURF_E2C', u'COMREL2_3', u'TDEC_3', u'PRTFLG_3', u'TTEX_3C', u'TTEX_3B', u'TTEX_3A', u'SURFM_3', u'SURFM_Q3', u'SURFM_ST3', u'SURF_E3A', u'SURF_E3B', u'SURF_E3C', u'BEDROCK_3', u'STTEX_3C', u'STTEX_3B', u'STTEX_3A', u'SSURFM_3', u'SSURFM_Q3', u'SSURFM_ST3', u'SSURF_E3A', u'SSURF_E3B', u'SSURF_E3C', u'TTTEX_3C', u'TTTEX_3B', u'TTTEX_3A', u'TSURFM_3', u'TSURFM_Q3', u'TSURFM_ST3', u'TSURF_E3A', u'TSURF_E3B', u'TSURF_E3C', u'GEOP_1', u'GEOP_Q1', u'GEOP_ST1', u'GEOP_INZ1', u'GEOP_INZ1A', u'GEOP_SCM1A', u'GEOP_INZ1B', u'GEOP_SCM1B', u'GEOP_INZ1C', u'GEOP_SCM1C', u'GEOP_2', u'GEOP_Q2', u'GEOP_ST2', u'GEOP_INZ2', u'GEOP_INZ2A', u'GEOP_SCM2A', u'GEOP_INZ2B', u'GEOP_SCM2B', u'GEOP_INZ2C', u'GEOP_SCM2C', u'GEOP_3', u'GEOP_Q3', u'GEOP_ST3', u'GEOP_INZ3', u'GEOP_INZ3A', u'GEOP_SCM3A', u'GEOP_INZ3B', u'GEOP_SCM3B', u'GEOP_INZ3C', u'GEOP_SCM3C', u'DRAIN_1', u'DRAIN_SEP', u'DRAIN_2', u'SLPLL_1', u'SLPUL_1', u'SLPLL_2', u'SLPUL_2', u'SLPSTB_CLS', u'RDSTB_FLG', u'SFCERO_POT', u'LSSED_CLS', u'SESED_CLS', u'DRAIN_1A', u'DRAIN_SEP1', u'DRAIN_1B', u'DRAIN_2A', u'DRAIN_SEP2', u'DRAIN_2B', u'DRAIN_3A', u'DRAIN_SEP3', u'DRAIN_3B']

import arcpy

table = r'\\spatialfiles.bcgov\work\env\esd\eis\tei\TEI_Working\BAuger\contractor_package_20200319\Operational_Data_6581.gdb\TEI_Long_Tbl'

for f in fieldslist:
    try:
        arcpy.RemoveDomainFromField_management(table,f)
    except:
        print("{} does not have a domain").format(f)        
