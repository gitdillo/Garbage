import os
import random
from image_utils import *

source_annotation_path = 
output_directory =

l=os.listdir(source_annotation_path)

img_size = 1000
random_jiggle_pixels = img_size/2
outputs_per_image = 4

for item in l:
    voc_file = os.path.join(source_annotation_path, item)
    data = parse_VOC(voc_file)
    image_file = data['path']
    roi = get_image_ROI(voc_file)
    roi_width = roi[1][0] - roi[0][0]
    roi_height = roi[1][1] - roi[0][1]
    # crop_image does checks for out of range values so we can pass it bullshit
    # values without checking

    for i in range(outputs_per_image):
        x = max(0, int(roi[0][0] + (roi_width/2) - (img_size/2) + random.randint(-random_jiggle_pixels, random_jiggle_pixels)))
        y = max(0, int(roi[0][1] + (roi_height/2) - (img_size/2) + random.randint(-random_jiggle_pixels, random_jiggle_pixels)))
        width = img_size
        height = img_size

        outname = os.path.splitext(os.path.basename(image_file))[0] + '_' + str(i+1)

        crop_image(image_file, voc_file, x, y, width, height, output_directory, output_filename=outname)
