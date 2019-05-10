import os
import argparse
import json
import cv2

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
            print args[0:]

    ds = gdal.Open(opts.tif)

    rasterX = ds.RasterXSize
    rasterY = ds.RasterYSize

    sliced = 0

    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    output = opts.output
    hits = []

    sliceSize = opts.sliceSize
    overlap = opts.overlap

    yCeil = int(math.ceil(rasterY / sliceSize))
    xCeil = int(math.ceil(rasterX / sliceSize))

    initialCoords = geotiff.GetCoords(ds)
    printv("Slice length: {0}x{1}, Raster size: {2}x{3}, origin coords: {4}, {5}".format(
        xCeil, yCeil, rasterX, rasterY, initialCoords[0], initialCoords[1]
    ))


    for y in range(0, yCeil):
        ys = zeroNegatives(y * sliceSize - overlap)
        my = 1 if y == 0 else 2

        for x in range(0, xCeil):
            xs = zeroNegatives(x * sliceSize - overlap)

            mx = 1 if x == 0 else 2
            
            w = limit(rasterX, xs, sliceSize + mx * overlap)
            h = limit(rasterY, ys, sliceSize + my * overlap)
            
            m = geotiff.SliceDataset(
                ds,
                xs,
                ys,
                w,
                h
            )

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
                print(hits, "hits at {0}x{1}".format(x,y))
                with open(output, "w") as fileOutput:
                    fileOutput.write(json.dumps(geojson, cls=DecimalEncoder))

            sliced = sliced + 1
            if sliced % 100 == 99:
                print("Sliced another 100, at", xs, ys)

    with open(output, "w") as fileOutput:
        fileOutput.write(json.dumps(geojson, cls=DecimalEncoder))

def addFeatureFromBoundingBox(geojson, ds, bbox, properties = {}):
    gt = ds.GetGeoTransform()

    cols = ds.RasterXSize
    rows = ds.RasterYSize

    coords = geotiff.GetCoordinatesFromPixelBox(
        gt,
        cols,
        rows,
        bbox["x"],
        bbox["y"],
        bbox["width"],
        bbox["height"],
    )

    topLeft     = [coords[0], coords[1]]
    topRight    = [coords[2], coords[1]]
    bottomLeft  = [coords[0], coords[3]]
    bottomRight = [coords[2], coords[3]]

    geojson["features"].append({
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    topLeft,
                    topRight,
                    bottomRight,
                    bottomLeft
                ]
            ]
        },

        "properties": properties
    })

    return [topLeft, topRight, bottomRight, bottomLeft]

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def limit(upper, at, value):
    return upper - at if at + value > upper else value

def zeroNegatives(v):
    return 0 if v < 0 else v

if __name__ == "__main__":
   main(sys.argv[1:])
