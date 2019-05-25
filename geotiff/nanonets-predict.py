import os
import argparse
import json

from osgeo import gdal, ogr, osr
import sys, getopt

import geotiff
from geojson import newCollection, addFeatureFromBoundingBox

import time
import math
from decimal import Decimal

import numpy as np
import json
import nanonets as nano

def main(argv):
    predOpts = PredictionOptions()

    try:
        opts, args = getopt.getopt(argv, "t:m:", [
            "output=",
            "tif=",
            "slice=",
            "overlap=",
            "temp-slice=", 
            "verbose",
            "cut=",
            "auth=",
            "model=",
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
        elif opt == "--slice":
            predOpts.sliceSize = int(arg)
        elif opt == "--overlap":
            predOpts.overlap = int(arg)
        elif opt == "--output":
            predOpts.output = arg
        elif opt == "--verbose":
            predOpts.verbose = True
        elif opt == "--temp-slice":
            predOpts.tempSlice = arg
        elif opt == "--auth":
            predOpts.auth = arg
        elif opt == "--model":
            predOpts.model = arg
        elif opt == "--cut":
            x, y, rows, columns = map(lambda a : int(a), arg.split(","))

            predOpts.x       = x
            predOpts.y       = y
            predOpts.rows    = rows
            predOpts.columns = columns

    if (predOpts.tif == None or predOpts.auth == None or predOpts.model == None):
        print('predict.py --auth <api key> --model <model> --tif <geotiff.tif>')
        sys.exit(2)

    runPrediction(predOpts)

class PredictionOptions:
    output = "./nanonets-predict-results.json"
    tempSlice = "./tempslice.jpg"
    auth = None
    model = None
    tif = None
    sliceSize = 500
    overlap = 50
    verbose = False
    x = 0
    y = 0
    rows = 1
    columns = 1

def runPrediction(opts):
    gdal.UseExceptions();
    ds = gdal.Open(opts.tif)

    def printv(*args):
        if opts.verbose == True:
            print(args[0:])

    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    output = opts.output

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

    def writeJSON():
        with open(output, "w") as fileOutput:
            fileOutput.write(json.dumps(geojson, cls=DecimalEncoder))

    class Memo:
        sliced = 0

    memo = Memo()
    def callback(m, xs, ys, w, h):
        memImage, coords = geotiff.DatasetToJPEG(m, opts.tempSlice)

        printv("Slicing: {0}x{1} {2}w {3}h, coords: [{4}, {5}]".format(
            xs, ys, w, h, coords[0], coords[1]
        ))

        res = nano.predictImage(opts.auth, opts.model, memImage.getPath())
        if res["message"] != "Success":
            printv("Failed to predict:", memImage.getPath())
            return

        for result in res["result"]:
            if result["message"] != "Success":
                printv("Failed prediction.")
                continue

            predictions = result["prediction"]
            for prediction in predictions:
                addedCoords = addFeatureFromBoundingBox(geojson, m, {
                    "x": prediction["xmin"],
                    "y": prediction["ymin"],
                    "width": prediction["xmax"] - prediction["xmin"],
                    "height": prediction["ymax"] - prediction["ymin"]
                },
                    {
                    "label": prediction["label"],
                    "score": Decimal(prediction["score"] * 1)
                }
                )

            if len(predictions) > 0:
                print(len(predictions), "hits at {0}x{1}".format(xs,ys))
                writeJSON()


        memo.sliced = memo.sliced + 1
        if memo.sliced % 100 == 99:
            print("Sliced another 100, at", xs, ys)

    geotiff.LoopSlices(
        ds, sliceSize, overlap, callback,
        opts.x, opts.y, opts.columns, opts.rows,
    )

    writeJSON()

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

if __name__ == "__main__":
   main(sys.argv[1:])
