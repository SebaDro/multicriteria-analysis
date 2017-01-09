# Import system modules
import sys
import arcpy
import os
from arcpy import env
from arcpy.sa import *

"""
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
"""

inWorkspace = arcpy.GetParameterAsText(0)
outWorkspace = arcpy.GetParameterAsText(1)
maskFile = arcpy.GetParameterAsText(2)
sourceStart = arcpy.GetParameterAsText(3)
sourceEnd = arcpy.GetParameterAsText(4)
tablePath = arcpy.GetParameterAsText(5)

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

featureList = arcpy.ListFeatureClasses("*", "All")


def featureToRaster(feature):
    desc = arcpy.Describe(feature)
    layerName = desc.name
    arcpy.AddMessage("Layer {0} will be converted to Raster...".format(layerName))
    print (layerName)
    outRaster = os.path.join(outWorkspace, os.path.splitext(layerName)[0] + "_raster")
    # if field <weight> already exists delete it,
    # to join the <weight> field from the <weight> table
    fields = arcpy.ListFields(feature, "weight")
    if len(fields) == 1:
        arcpy.DeleteField_management(feature, ["weight"])
    # join the <weight> field from the <weight> table
    arcpy.JoinField_management(feature, joinFieldIn, weightTable, joinField, ["weight"])
    # create a raster dataset from the polygon
    if desc.shapeType == "Polygon":
        rasterResult = arcpy.PolygonToRaster_conversion(feature, valField, outRaster, assignmentTypePolygon, "",
                                                        cellSize)
    elif desc.shapeType == "Polyline":
        rasterResult = arcpy.PolylineToRaster_conversion(feature, valField, outRaster, assignmentTypePolyline, "",
                                                         cellSize)
    arcpy.AddMessage("Raster {0} has been created.".format(rasterResult))
    return rasterResult


maskRaster = featureToRaster(maskFile)
desc = arcpy.Describe(maskRaster)
inRasters = os.path.join(desc.path, desc.file) + ";"
mosaic = None

# convert polygons into raster datasets
# iterate over all polygons
for feature in featureList:
    try:
        rasterResult = featureToRaster(feature)
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

arcpy.AddMessage("Mosaic will be created...")
# raster datasets must have the same extent
mosaic = arcpy.MosaicToNewRaster_management(inRasters, outWorkspace, "mosaic", "", "8_BIT_UNSIGNED", "5", "1",
                                            "MAXIMUM", "MATCH")
arcpy.AddMessage("Mosaic has been created.")
print("Mosaic created")

# Check out the ArcGIS Spatial Analyst extension license
arcpy.CheckOutExtension("Spatial")

try:
    # Execute CostDistance for start point
    print("create OutCostDistanceStart")
    arcpy.AddMessage("OutCostDistanceStart will be created.")
    outCostDistanceStart = CostDistance(sourceStart, mosaic, "", "")
    print("save OutCostDistanceStart")
    outCostDistanceStart.save(os.path.join(outWorkspace, "distance_start"))
    arcpy.AddMessage("OutCostDistanceStart has been created.")
    print("OutCostDistanceStart created")
    # Execute CostDistance for end point
    print("create OutCostDistanceEnd")
    arcpy.AddMessage("OutCostDistanceStart will be created.")
    outCostDistanceEnd = CostDistance(sourceEnd, mosaic, "", "")
    print("save OutCostDistanceEnd")
    outCostDistanceEnd.save(os.path.join(outWorkspace, "distance_end"))
    arcpy.AddMessage("OutCostDistanceStart has been created.")
    print("OutCostDistanceEnd created")
    # Execute Corridor
    arcpy.AddMessage("Corridor will be created.")
    outCorridor = Corridor(outCostDistanceStart, outCostDistanceEnd)
    # Save the output
    outCorridor.save(os.path.join(outWorkspace, "corridor"))
    arcpy.AddMessage("Corridor has been created.")
# Return geoprocessing specific errors
except arcpy.ExecuteError:
    arcpy.AddError(arcpy.GetMessages(2))  # Return any other type of error
except:  # By default any other errors will be caught here
    e = sys.exc_info()[1]
    print(e.args[0])
finally:
    arcpy.CheckInExtension("Spatial")
