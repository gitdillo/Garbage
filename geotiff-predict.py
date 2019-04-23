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
    modelConfig, weights = image.loadWeights(model)
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

            path, coords, auxPath = geotiff.DatasetToJPEG(m)
            annotations = image.imageDetection(modelConfig, weights, path)
            print(coords, annotations)

def limit(upper, at, value):
    return upper - at if at + value > upper else value

def zeroNegatives(v):
    return 0 if v < 0 else v

def loadWeights(mpath):
    config_path = mpath + "config.json"

    with open(config_path) as config_buffer:
        config = json.load(config_buffer)

    net_h, net_w = 416, 416 # a multiple of 32, the smaller the faster
    obj_thresh, nms_thresh = 0.5, 0.45

    os.environ['CUDA_VISIBLE_DEVICES'] = config['train']['gpus']
    infer_model = load_model(mpath + str(config['train']['saved_weights_name']))

    print("Loaded", mpath)

    return config, infer_model

def imageDetection(config, model, image_path):
    net_h, net_w = 416, 416 # a multiple of 32, the smaller the faster
    obj_thresh, nms_thresh = 0.5, 0.45

    image = cv2.imread(image_path)

    # predict the bounding boxes
    boxes = get_yolo_boxes(model, [image], net_h, net_w, config['model']['anchors'], obj_thresh, nms_thresh)[0]

    # Put all bounding boxes and labels for this image in a json file
    annotations = list()
    for box in boxes:
        annotations.append({
            "label": config['model']['labels'][box.get_label()],
            "score": float(box.score),
            "xmax":box.xmax,
            "xmin":box.xmin,
            "ymax":box.ymax,
            "ymin":box.ymin
        })
    
    return annotations

if __name__ == "__main__":
   main(sys.argv[1:])
