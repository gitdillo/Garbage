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
import arger

def main(argv):
    predOpts = PredictionOptions()
    commands = [dict(
        command =  "auth",
        input =  True,
        required =  True,
    ),
    dict(
        command =  "model",
        input =  True,
        required =  True,
    ),
    dict(
        command =  "tif",
        alias =  ["t"],
        input =  True,
        required =  True,
    ),
    dict(
        command =  "slice",
        input =  True
    ),
    dict(
        command =  "overlap",
        input =  True
    ),
    dict(
        command =  "temp-slice",
        key = "tempSlice",
        input =  True
    ),
    dict(
        command =  "verbose",
    ),
    dict(
        command =  "cut",
        input =  True,
        example = "200,200,2,2"
    ),
    dict(
        command =  "grid",
    ),
    dict(
        command =  "info",
    )]

    try:
        opts = arger.parseArgs(argv, commands)
    except Exception as err:
        arger.printHelp("nanonets-predict.py", commands)
        sys.exit(2)

    if opts.get("cut", None) != None:
        cut = opts.get("cut")
        x, y, rows, columns = amap(lambda a : int(a), cut.split(","))

        predOpts.x       = x
        predOpts.y       = y
        predOpts.rows    = rows
        predOpts.columns = columns
        del opts["cut"]

    predOpts.__dict__.update(opts)
    runPrediction(predOpts)

def amap(f, l):
    return list(map(f, l))

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
    grid = False
    info = False

def runPrediction(opts):
    gdal.UseExceptions();
    ds = gdal.Open(opts.tif)

    def printv(*args):
        if opts.verbose == True or opts.info == True:
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

    x = opts.x if opts.grid else int(math.floor(opts.x / sliceSize))
    y = opts.y if opts.grid else int(math.floor(opts.y / sliceSize))

    if opts.grid == False:
        opts.columns = opts.columns + 1
        opts.rows    = opts.rows + 1

    initialCoords = geotiff.GetCoords(ds)
    printv("Grid size: {0}x{1}, Raster size: {2}x{3}, origin coords: {4}, {5}, starting at: {6}x{7}, slicing: {8} columns and {9} rows".format(
        xCeil, yCeil, rasterX, rasterY, initialCoords[0], initialCoords[1], x, y,
        opts.columns, opts.rows
    ))

    if opts.info == True:
        return

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

        # Sleep to be lenient with hits on API.
        time.sleep(0.2)

    geotiff.LoopSlices(
        ds, sliceSize, overlap, callback,
        x, y, opts.columns, opts.rows,
    )

    writeJSON()

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

if __name__ == "__main__":
   main(sys.argv[1:])
