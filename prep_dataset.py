from image_utils import dataset_crop_to_ROI, dataset_to_tiles
import os

dataset_path = '...'



# First, crop the edges, that do not contain any shapes, away from the ROI
roi_out_dir = os.path.join(dataset_path, 'roi_cropped')
dataset_crop_to_ROI(dataset_path, roi_out_dir, roi_padding=10)


# Second, chop up the cropped images into tiles
tile_out_dir = os.path.join(dataset_path, 'crop2tiles')
tile_width = 500
tile_height = 500
dataset_to_tiles(dataset_path, tile_width, tile_height, tile_out_dir)
