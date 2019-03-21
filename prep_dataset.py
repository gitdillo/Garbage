from image_utils import dataset_crop_to_ROI, dataset_to_tiles, generate_VOC_annotations
import os

dataset_path = '/windows_storage/IT/Keras_YOLO/litter_data/Training_Data/DJI_car_park_20_Feb_2019/'

# Uncomment this line if Pascal VOC .xml files have not been generated and the folder contains a "polygons.json" file
generate_VOC_annotations(dataset_path, os.path.join(dataset_path, 'polygons.json'))


# First, crop the edges, that do not contain any shapes, away from the ROI
roi_out_dir = os.path.join(dataset_path, 'roi_cropped')
dataset_crop_to_ROI(dataset_path, roi_out_dir, roi_padding=10)


# Second, chop up the cropped images into tiles
tile_width = 500
tile_height = 500
tile_out_dir = os.path.join(roi_out_dir, str(tile_width) + 'x' + str(tile_height) + '_crop2tiles')
dataset_to_tiles(roi_out_dir, tile_width, tile_height, tile_out_dir)
