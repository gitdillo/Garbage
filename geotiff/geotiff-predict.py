import os
import argparse
import json

from osgeo import gdal, ogr, osr
import sys, getopt

import geotiff
import time
import math
from decimal import Decimal

from utils.utils import get_yolo_boxes, makedirs
from utils.bbox import draw_boxes
from keras.models import load_model

from model import loadWeights, imageDetection
import numpy as np
import json

from geojson import newCollection, addFeatureFromBoundingBox

def main(argv):
    predOpts = PredictionOptions()

    try:
        opts, args = getopt.getopt(argv, "t:m:", [
            "tif=",
            "model=",
            "slice=",
            "overlap=",
            "ignore-negatives", 
            "temp-slice=", 
            "output=",
            "verbose"
        ])
    except getopt.GetoptError:
        print('err: predict.py -tif <geotiff.tif> --model <config.json>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('predict.py -tif <geotiff.tif> --model <config.json>')
            sys.exit()
        elif opt in ("-t", "--tif"):
            predOpts.tif = arg
        elif opt in ("-m", "--model"):
            predOpts.model = arg
        elif opt == "--slice":
            predOpts.sliceSize = int(arg)
        elif opt == "--overlap":
            predOpts.overlap = int(arg)
        elif opt == "--ignore-negatives":
            predOpts.ignoreNegatives = True
        elif opt == "--output":
            predOpts.output = arg
        elif opt == "--temp-slice":
            predOpts.tempSlice = arg
        elif opt == "--verbose":
            predOpts.verbose = True

    if (predOpts.tif == None or predOpts.model == None):
        print('predict.py -tif <geotiff.tif> --model <config.json>')
        sys.exit(2)

    runPrediction(predOpts)

class PredictionOptions:
    tempSlice = "./tempslice.jpg"
    output = "./geotiff-predict-results.json"
    tif = None
    model = None
    sliceSize = 500
    overlap = 50
    ignoreNegatives = False
    verbose = False

def runPrediction(opts):
    modelConfig, weights = loadWeights(opts.model)
    gdal.UseExceptions();
    
    def printv(*args):
        if opts.verbose == True:
            print(args[0:])

    ds = gdal.Open(opts.tif)

    geojson = newCollection() 

    output = opts.output
    hits = []

    sliceSize = opts.sliceSize
    overlap = opts.overlap

    rasterX = ds.RasterXSize
    rasterY = ds.RasterYSize
    yCeil = int(math.ceil(rasterY / sliceSize))
    xCeil = int(math.ceil(rasterX / sliceSize))

    initialCoords = geotiff.GetCoords(ds)
    printv("Slice length: {0}x{1}, Raster size: {2}x{3}, origin coords: {4}, {5}".format(
        xCeil, yCeil, rasterX, rasterY, initialCoords[0], initialCoords[1]
    ))

    class Memo:
        sliced = 0

    memo = Memo()
    def callback(m, xs, ys, w, h):
        memImage, coords = geotiff.DatasetToJPEG(m, opts.tempSlice)

        printv("Slicing: {0}x{1} {2}w {3}h, coords: [{4}, {5}]".format(
            xs, ys, w, h, coords[0], coords[1]
        ))

        annotations = imageDetection(
            modelConfig,
            weights,
            memImage.getPath()
        )

        hits = 0
        for annotation in annotations:
            if annotation["score"] < 0 and opts.ignoreNegatives:
                print("Ignored a negative score detection.")
                continue

            addedCoords = addFeatureFromBoundingBox(geojson, m, {
                "x": annotation["xmin"],
                "y": annotation["ymin"],
                "width": annotation["xmax"] - annotation["xmin"],
                "height": annotation["ymax"] - annotation["ymin"]
            },
                {
                "label": annotation["label"],
                "score": Decimal(annotation["score"] * 1)
            }
            )

            printv("Annotation at", addedCoords)
            hits = hits + 1

        if hits > 0:
            print(hits, "hits at {0}x{1}".format(xs,ys))
            with open(output, "w") as fileOutput:
                fileOutput.write(json.dumps(geojson, cls=DecimalEncoder))

        memo.sliced = memo.sliced + 1
        if memo.sliced % 100 == 99:
            print("Sliced another 100, at", xs, ys)

    geotiff.LoopSlices(
        ds, sliceSize, overlap,
        callback
    )

    with open(output, "w") as fileOutput:
        fileOutput.write(json.dumps(geojson, cls=DecimalEncoder))

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

if __name__ == "__main__":
   main(sys.argv[1:])
