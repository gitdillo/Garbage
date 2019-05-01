import os
import argparse
import json
import cv2

from osgeo import gdal, ogr, osr
import sys, getopt

import geotiff
import time
import math

from utils.utils import get_yolo_boxes, makedirs
from utils.bbox import draw_boxes
from keras.models import load_model
from tqdm import tqdm

import model
import numpy as np

def main(argv):
    tif       = None
    model     = None
    sliceSize = 500
    overlap   = 50

    try:
        opts, args = getopt.getopt(argv, "t:m:", ["tif=","model=","slice=","overlap="])
    except getopt.GetoptError:
        print('predict.py -tif <geotiff.tif> --model <config.json>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('predict.py -tif <geotiff.tif> --model <config.json>')
            sys.exit()
        elif opt in ("-t", "--tif"):
            tif = arg
        elif opt in ("-m", "--model"):
            model = arg
        elif opt == "--slice":
            sliceSize = int(arg)
        elif opt == "--overlap":
            overlap = int(arg)

    if (tif == None or model == None):
        print('predict.py -tif <geotiff.tif> --model <config.json>')
        sys.exit(2)

    runPrediction(tif, model, sliceSize, overlap)

def runPrediction(tif, model, sliceSize, overlap):
    modelConfig, weights = model.loadWeights(model)
    gdal.UseExceptions();

    ds = gdal.Open(tif)

    rasterX = ds.RasterXSize
    rasterY = ds.RasterYSize

    for y in range(0, math.ceil(rasterY / sliceSize)):
        ys = zeroNegatives(y * sliceSize - overlap)
        my = 1 if y == 0 else 2

        for x in range(0, math.ceil(rasterX / sliceSize)):
            xs = zeroNegatives(x * sliceSize - overlap)
            
            mx = 1 if x == 0 else 2
            m = geotiff.SliceDataset(
                ds,
                xs,
                ys,
                limit(rasterX, xs, sliceSize + mx * overlap),
                limit(rasterY, ys, sliceSize + my * overlap)
            )

            memImage, coords = geotiff.DatasetToJPEG(m)
            annotations = model.imageDetection(
                modelConfig,
                weights,
                memImage.getPath()
            )

            print(coords, annotations)

def limit(upper, at, value):
    return upper - at if at + value > upper else value

def zeroNegatives(v):
    return 0 if v < 0 else v

if __name__ == "__main__":
   main(sys.argv[1:])
