Utilities for generating and handling data relevant to drone litter detection.

Scripts for Photoscan are kept separately under directory "Photoscan_scripts"

Various utilities for manipulation of the data after information has been extracted from Photoscan are all inside "image_utils.py"


Workflow:

In a Photoscan project, draw polygons around items of interest and then tag them by setting a label in the polygon's Preferences menu.

Edit script "photoscan_export_polygons.py" to point variable "output_file" to whatever path the output file should be.

Run (CTRL-R) script "photoscan_export_polygons.py", this will create a "polygons.json" file at the location specified in "output_file".

This file has an entry for each image in the Photoscan project and each entry contains the polygon vertices and label of each item visible in the image.



Once the polygons file has been created, xml files in PASCAL VOC format can be created by calling "generate_VOC_annotations" from "image_utils", e.g.:

import image_utils
image_path = ...
polygons_file = ...
generate_VOC_annotations(image_path, polygons_file)

This will create the xml files in the "image_path" directory.






