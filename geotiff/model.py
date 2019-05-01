import os
import argparse
import json
import cv2

from utils.utils import get_yolo_boxes, makedirs
from utils.bbox import draw_boxes
from keras.models import load_model
from tqdm import tqdm

import re

import numpy as np

def loadWeights(mpath):
    #config_path = re.sub("(config.json)?$", "config.json", mpath)
    config_path = mpath

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

