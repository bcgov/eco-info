ArcGIS Toolbox Script Considerations

General Notes
- scripts should be written to accept user parameters where possible
- field validation can be added in the toolbox interface
- format should be standard arcgis toolbox, not python toolbox
- contractor scripts linked below is an example of a script delivered in a toolbox



Script Syntax
- sys.argv can still be used for parameter input
- if script requires command prompt still sys.argv can be used
- arcpy.getparameterastext() is expected if script will be exclusive to toolbox
- error handling should return messages to geoprocessing window



Links
https://github.com/bcgov-c/teis-env/tree/master/Scripts/contractor_package
https://pro.arcgis.com/en/pro-app/latest/arcpy/geoprocessing_and_python/accessing-parameters-in-a-script-tool.htm
https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/error-handling-with-python.htm
https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/python-migration-for-arcgis-pro.htm

