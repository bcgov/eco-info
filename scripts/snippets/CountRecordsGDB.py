#-------------------------------------------------------------------------------
# Name:        Count Records in GDB
# Purpose:
#
# Author:      bauger
#
# Created:     19-05-2021
# Copyright:   (c) bauger 2021
# Licence:     <your licence>
#-------------------------------------------------------------------------------

# Import
import arcpy,os


# Get Inputs
ingdb= arcpy.GetParameterAsText(0)
#ingdb =r"\\spatialfiles.bcgov\work\env\esd\eis\wld\eis_arcproj\eis_21_000_data_requests\req_21_016_Wolverine_Canfor\outputs\data\telem_data_request_20210427.gdb"


# Get list of FCs
arcpy.env.workspace = ingdb
fclist = arcpy.ListFeatureClasses()

for fc in fclist:
    fcpath = os.path.join(ingdb,fc)
    desc = arcpy.Describe(fcpath)
    result = arcpy.GetCount_management(fcpath)
    count = int(result.getOutput(0))
    print (
    "Name:{} \nRecord Count:{} \nFeature Type:{}\nFeature Shape Type:{}\n").format(fc,count,desc.featureType,desc.shapeType)
