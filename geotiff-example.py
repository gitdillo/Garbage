from osgeo import gdal,ogr,osr
import sys

import utils
import time

gdal.UseExceptions();

tifPath = "/path/to/tif/file"

ds = gdal.Open(tifPath)

sliced = utils.SliceDataset(
    ds,
    45000,
    45000,
    500,
    500
)

#sliced = utils.SliceDatasetToFile(
#    ds,
#    f"./output/chunk.tif",
#    45000,
#    45000,
#    500,
#    500
#)

#path, coords, auxPath = utils.DatasetToJPEG(sliced, "./output.jpeg")
path, coords, auxPath = utils.DatasetToJPEG(sliced)
print(path, coords, auxPath)

