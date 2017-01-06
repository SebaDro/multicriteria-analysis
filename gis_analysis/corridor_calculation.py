# Import system modules
import sys
import arcpy
import os
from arcpy import env
from arcpy.sa import *

# get parameters from the script parameters
# and ensure the correct number of parameters
if len(sys.argv) >= 6:
    inWorkspace = sys.argv[1]
    outWorkspace = sys.argv[2]
    maskFile = sys.argv[3]
    sourceStart = sys.argv[4]
    sourceEnd = sys.argv[5]
    tablePath = sys.argv[6]
    print "Input Workspace: {0}; Output workspace: {1}; Mask: {2}; Source start: {3}; Source end: {4}; Path table: {5} ".format(
        inWorkspace,
        outWorkspace,
        maskFile,
        sourceStart,
        sourceEnd,
        tablePath)
else:
    print "Usage: corridor_calculation <input_workspace> <output_workspace> <source_start> <source_end>"
    sys.exit()

# Set environment settings
env.workspace = inWorkspace
arcpy.env.mask = maskFile
desc = arcpy.Describe(maskFile)
print (desc.extent)
arcpy.env.extent = desc.extent
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(25832)
arcpy.env.overwriteOutput = True

# Set local variables
polygon = "ca_counties.shp"
valField = "weight"
assignmentTypePolygon = "MAXIMUM_AREA"
assignmentTypePolyline = "MAXIMUM_AREA"
# priorityField = "MALES"
cellSize = 5.0
joinFieldIn = "type"
joinField = "type"
weightTableName = "weight_table"

# create table for weights from excel
weightTable = arcpy.ExcelToTable_conversion(tablePath, os.path.join(outWorkspace, weightTableName))

polygonList = arcpy.ListFeatureClasses("*", "Polygon")
polylineList = arcpy.ListFeatureClasses("*", "Polyline")


def polygonToRaster(polygon):
    desc = arcpy.Describe(polygon)
    layerName = desc.name
    print (layerName)
    outRaster = os.path.join(outWorkspace, os.path.splitext(layerName)[0] + "_raster")
    # if field <weight> already exists delete it,
    # to join the <weight> field from the <weight> table
    fields = arcpy.ListFields(polygon, "weight")
    if len(fields) == 1:
        arcpy.DeleteField_management(polygon, ["weight"])
    # join the <weight> field from the <weight> table
    arcpy.JoinField_management(polygon, joinFieldIn, weightTable, joinField, ["weight"])
    # create a raster dataset from the polygon
    rasterResult = arcpy.PolygonToRaster_conversion(polygon, valField, outRaster, assignmentTypePolygon, "", cellSize)
    print rasterResult
    return rasterResult


def polylineToRaster(polyline):
    desc = arcpy.Describe(polyline)
    layerName = desc.name
    outRaster = os.path.join(outWorkspace, os.path.splitext(layerName)[0] + "_raster")
    # if field <weight> already exists delete it,
    # to join the <weight> field from the <weight> table
    fields = arcpy.ListFields(polyline, "weight")
    if len(fields) == 1:
        arcpy.DeleteField_management(polyline, ["weight"])
    # join the <weight> field from the <weight> table
    arcpy.JoinField_management(polyline, joinFieldIn, weightTable, joinField, ["weight"])
    # create a raster dataset from the polyline
    rasterResult = arcpy.PolylineToRaster_conversion(polyline, valField, outRaster, assignmentTypePolyline, "",
                                                     cellSize)
    print rasterResult
    return rasterResult


maskRaster = polygonToRaster(maskFile)
desc = arcpy.Describe(maskRaster)
#desc = arcpy.Describe(maskFile)
inRasters = os.path.join(desc.path, desc.file) + ";"
mosaic = None

# convert polygons into raster datasets
# iterate over all polygons
for polygon in polygonList:
    try:
        rasterResult = polygonToRaster(polygon)
        desc = arcpy.Describe(rasterResult)
        inRasters = inRasters + os.path.join(desc.path, desc.file) + ";"
    # Return geoprocessing specific errors
    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
    # Return any other type of error
    except:
        # By default any other errors will be caught here
        e = sys.exc_info()[1]
        print(e.args[0])

# convert polylines into raster datasets
# iterate over all polylines
for polyline in polylineList:
    try:
        rasterResult = polylineToRaster(polyline)
        desc = arcpy.Describe(rasterResult)
        inRasters = inRasters + os.path.join(desc.path, desc.file) + ";"
    # Return geoprocessing specific errors
    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
    # Return any other type of error
    except:
        # By default any other errors will be caught here
        e = sys.exc_info()[1]
        print(e.args[0])

inRasters = inRasters[0:-1]
print inRasters

# raster datasets must have the same extent
mosaic = arcpy.MosaicToNewRaster_management(inRasters, outWorkspace, "mosaic", "", "8_BIT_UNSIGNED", "5", "1",
                                            "MAXIMUM", "MATCH")
print("Mosaic created")


# Check out the ArcGIS Spatial Analyst extension license
arcpy.CheckOutExtension("Spatial")

try:
    # Execute CostDistance for start point
    print("create OutCostDistanceStart")
    outCostDistanceStart = CostDistance(sourceStart, mosaic, "", "")
    print("save OutCostDistanceStart")
    outCostDistanceStart.save(os.path.join(outWorkspace, "distance_start"))
    print("OutCostDistanceStart created")
    # Execute CostDistance for end point
    print("create OutCostDistanceEnd")
    outCostDistanceEnd = CostDistance(sourceEnd, mosaic, "", "")
    print("save OutCostDistanceEnd")
    outCostDistanceEnd.save(os.path.join(outWorkspace, "distance_end"))
    print("OutCostDistanceEnd created")
# Return geoprocessing specific errors
except arcpy.ExecuteError:
    arcpy.AddError(arcpy.GetMessages(2))
# Return any other type of error
except:
    # By default any other errors will be caught here
    e = sys.exc_info()[1]
    print(e.args[0])
finally:
    arcpy.CheckInExtension("Spatial")

