import os
import cv2

from osgeo import gdal, ogr, osr
import sys, getopt

import geotiff
import json
import numpy as np

from decimal import Decimal
import arger

def main(argv):
    predOpts = PredictionOptions()
    commands = [
    dict(
        command =  "tif",
        alias =  ["t"],
        input =  True,
        required =  True,
    ),
    dict(
        command =  "geojson",
        input =  True,
        required =  True,
    ),
    dict(
        command =  "output",
        input =  True,
        required =  True,
    ),
    dict(
        command =  "padding",
        alias = ["p"],
        input =  True
    )
    ]

    try:
        opts = arger.parseArgs(argv, commands)
    except Exception as err:
        arger.printHelp("expand-images.py", commands)
        sys.exit(2)

    if opts.get("padding"):
        opts["padding"] = int(opts["padding"])

    predOpts.__dict__.update(opts)
    runPrediction(predOpts)

def amap(f, l):
    return list(map(f, l))

class PredictionOptions:
    output = None
    tif = None
    geojson = None
    padding = 0

def runPrediction(opts):
    gdal.UseExceptions();
    ds = gdal.Open(opts.tif)

    with open(opts.geojson, "r") as file:
        geojson = json.load(file)

    if not os.path.exists(opts.output):
        os.makedirs(opts.output)

    grid = {}
    for feature in geojson["features"]:
        boxes = geotiff.getPixelBoxesFromShapes(
            ds,
            feature["geometry"]["coordinates"]
        )

        for box in boxes:
            x = int(box.xmin / 500)
            y = int(box.ymin / 500)
            col = grid.get(x, {})
            row = col.get(y, [])

            grid[x]    = col
            grid[x][y] = row

            row.append(box)

    stored = 0
    for col in grid:
        cols = grid[col]
        for row in cols:
            nx = int(col * 500)
            ny = int(row * 500)
            width = 500
            height = 500

            slice = geotiff.SliceDataset(ds, nx, ny, width, height)
            memImage, c = geotiff.DatasetToJPEG(slice, output = "./tempslice.jpg")

            image = cv2.imread(memImage.getPath())
            thickness = 2

            for box in cols[row]:
                x1, x2 = amap(limiter(width, thickness), [
                    box.xmin - nx - opts.padding,
                    box.xmax - nx + opts.padding
                ])

                y1, y2 = amap(limiter(height, thickness), [
                    box.ymin - ny - opts.padding,
                    box.ymax - ny + opts.padding
                ])

                cv2.rectangle(
                    img       = image, 
                    pt1       = (x1, y1),
                    pt2       = (x2, y2),
                    color     = [0,0,255],
                    thickness = thickness
                )

            outputFile = os.path.join(opts.output, "result-{0}.jpg".format(stored))
            cv2.imwrite(outputFile, np.uint8(image))
            os.rename(
                memImage.getPath() + ".aux.xml",
                outputFile + ".aux.xml"
            )

            stored = stored + 1

    if stored > 0:
        os.remove("./tempslice.jpg")

def limiter(width, thickness):
    def cb(num):
        return 0 + thickness if num + thickness < 0 else width - thickness if num + thickness > width else num

    return cb

if __name__ == "__main__":
   main(sys.argv[1:])
