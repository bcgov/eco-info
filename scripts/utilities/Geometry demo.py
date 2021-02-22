import arcpy

infc = 'BC_Grids_All_20k_to_BC'

# Example of input, index starts at 0
# Test comment
inputfc= arcpy.GetParameterAsText(0)

# If map sheet count >1 use dissolve sso its pretty for Deepa, if 1 sheet copy geometry


# Pass a feature layer created in mememory into the search cursor, it will grab geometry from those records, put into an array
# Features passed into array are a series of points
array = arcpy.Array()

for row in arcpy.da.SearchCursor(infc, ["SHAPE@"]):
    row[0].generalize(.1)
    for point in row[0]:
        for pts in point:
            array.add(pts)

# Convert array into polygon
poly = arcpy.Polygon(array)

# Insert polygon into destination feature along wtih all the other attributes from excel file
cursor = arcpy.da.InsertCursor('test', ['SHAPE@'])
cursor.insertRow([poly.convexHull()])
