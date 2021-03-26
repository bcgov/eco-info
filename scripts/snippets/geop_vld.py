#Import modules
import arcpy

#Get inputs
#intable = arcyp.GetParameterAsText(0)
intable = r'\\spatialfiles.bcgov\work\env\esd\eis\tei\TEI_Working\BAuger\contractor_package_20200319\polly_fix\Operational_Data_6581_03_25_test.gdb\TEI_Long_Tbl_2'

#Create dictionary for geop fields
fieldlist = [["GEOP_1","GEOP_VLD1A"],["GEOP_1","GEOP_VLD1B"],["GEOP_1","GEOP_VLD1C"],["GEOP_2","GEOP_VLD2A"],["GEOP_2","GEOP_VLD2B"],["GEOP_2","GEOP_VLD2C"],["GEOP_3","GEOP_VLD3A"],["GEOP_3","GEOP_VLD3B"],["GEOP_1","GEOP_VLD3C"]]


codeblock = """
def getvld(i,j):
    if j=="":
        a=None
    else:
        a=i+j
    return a    
    """

for i in fieldlist:
    expression=("getvld(!{}!,!{}!)").format(i[0],i[1]) 
    arcpy.CalculateField_management(intable,i[1], expression, "PYTHON_9.3",codeblock)
    print("{} has been calculated!").format(i[1])


