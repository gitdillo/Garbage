from pascal_voc_writer import Writer
from PIL import Image, ImageDraw, ImageFont
import json
import os
import xml.etree.ElementTree as ET
import cv2
import Tkinter
import pdb
import numpy as np
import math
import random

def select_largest_obj(img_bin, lab_val=255, fill_holes=False, smooth_boundary=False, kernel_size=15):
  '''Select the largest object from a binary image and optionally
  fill holes inside it and smooth its boundary.
  Args:
  img_bin (2D array): 2D numpy array of binary image.
      lab_val ([int]): integer value used for the label of the largest 
              object. Default is 255.
      fill_holes ([boolean]): whether fill the holes inside the largest 
              object or not. Default is false.
      smooth_boundary ([boolean]): whether smooth the boundary of the 
              largest object using morphological opening or not. Default 
              is false.
      kernel_size ([int]): the size of the kernel used for morphological 
              operation. Default is 15.
  Returns:
      a binary image as a mask for the largest object.
  '''
  n_labels, img_labeled, lab_stats, _ = \
      cv2.connectedComponentsWithStats(img_bin, connectivity=8,
                                       ltype=cv2.CV_32S)
  largest_obj_lab = np.argmax(lab_stats[1:, 4]) + 1
  largest_mask = np.zeros(img_bin.shape, dtype=np.uint8)
  largest_mask[img_labeled == largest_obj_lab] = lab_val
  # import pdb; pdb.set_trace()
  if fill_holes:
      bkg_locs = np.where(img_labeled == 0)
      bkg_seed = (bkg_locs[0][0], bkg_locs[1][0])
      img_floodfill = largest_mask.copy()
      h_, w_ = largest_mask.shape
      mask_ = np.zeros((h_ + 2, w_ + 2), dtype=np.uint8)
      cv2.floodFill(img_floodfill, mask_, seedPoint=bkg_seed,
                    newVal=lab_val)
      holes_mask = cv2.bitwise_not(img_floodfill)  # mask of the holes.
      largest_mask = largest_mask + holes_mask
  if smooth_boundary:
      kernel_ = np.ones((kernel_size, kernel_size), dtype=np.uint8)
      largest_mask = cv2.morphologyEx(largest_mask, cv2.MORPH_OPEN,
                                      kernel_)

  return largest_mask

def vertices2boundingbox(vertex_list):
    '''Takes a vertex list defining a polygon (list of 2-element coord lists)
    and converts to a bounding box in the form of xmin, ymin, xmax, ymax.
    '''
    xmin = vertex_list[0][0]
    xmax = vertex_list[0][0]
    ymin = vertex_list[0][1]
    ymax = vertex_list[0][1]
    for v in vertex_list:
        xmin = min(xmin, v[0])
        xmax = max(xmax, v[0])
        ymin = min(ymin, v[1])
        ymax = max(ymax, v[1])
    return (xmin, ymin, xmax, ymax)

def generate_VOC_annotations(image_path, polygons_file):
    ''' Takes a json file containing polygons for the images in "image_path"
    and creates xml files in PASCAL VOC format in the "image_path".
    One VOC is generated per image.
    '''
    with open(polygons_file, 'r') as f:
        data=json.load(f)

    for d in data:
        img_path = os.path.join(image_path, d['image'])
        image = Image.open(img_path)
        writer = Writer(image.filename, image.width, image.height)
        for shape in d['shapes']:
            bb = vertices2boundingbox(shape['vertices'])
            writer.addObject(shape['label'], bb[0], bb[1], bb[2], bb[3])
        outpath = str(os.path.splitext(img_path)[0] + '.xml')
        writer.save(outpath)

def parse_VOC(voc_file):
    '''
    Parses a PASCAL VOC annotation file (xml) generated by
    "generate_VOC_annotations" corresponding to one tagged image. Returns a
    dictionary of the following fields:
    image: a filename
    shapes: a list where each item has a label and bounding box in two pairs of
    (xmin, ymin) and (xmax, ymax)
    '''
    tree = ET.parse(voc_file)
    root = tree.getroot()
    image_name = root.find('filename').text
    full_path = root.find('path').text
    d={'image': image_name, 'path': full_path}
    shapelist = []
    for obj in root.findall('object'):
        label = obj.find('name').text
        xmin = int(obj.find('bndbox').find('xmin').text)
        ymin = int(obj.find('bndbox').find('ymin').text)
        xmax = int(obj.find('bndbox').find('xmax').text)
        ymax = int(obj.find('bndbox').find('ymax').text)
        shapelist.append({"label": label, "xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax})
    d['shapes'] = shapelist
    return d

def display_annotated_image(image_file, annotation_file=None, save=False):
    '''
    draw_image_annotations(image_file, annotation_file, save=True)
    Draws bounding boxes around objects tagged in "annotation_file" This is
    expected to be either in PASCAL VOC xml format, generated by method
    "generate_VOC_annotations" or .json containing a list of dicts with fields:
    "label", "score", "xmin", "xmax", "ymin", "ymax".
    If the "save" flag is true, the result is saved in the same directory as the
    original image file with "_annotated" added to the filename. Otherwise, the
    result is rendered via the Image.show() method of the PIL library:
    https://pillow.readthedocs.io/en/3.1.x/reference/Image.html#PIL.Image.Image.show
    '''
    data = None

    if annotation_file is None:
        if os.path.isfile(os.path.splitext(image_file)[0] + '.json'):
            annotation_file = os.path.splitext(image_file)[0] + '.json'
        elif os.path.isfile(os.path.splitext(image_file)[0] + '.xml'):
            annotation_file = os.path.splitext(image_file)[0] + '.xml'
        else:
            print('No mathing annotation file found for image file: ' + str(image_file))
            return None

    if os.path.splitext(annotation_file)[1] == '.xml':
        data = parse_VOC(annotation_file)
        data = data['shapes']       # unlike .json, the VOC file has an outer layer with keys: 'shapes', 'path', 'image'. We only need "shapes" here
    elif os.path.splitext(annotation_file)[1] == '.json':
        with open(annotation_file, 'r') as f:
            data=json.load(f)
    else:
        print("Annotation file expected to be .xml or .json but passed file ain't:\n" + str(annotation_file))
        return

    image_filename = os.path.basename(image_file)
    image = cv2.imread(image_file)
    for item in data:
        cv2.rectangle(image, (item['xmin'], item['ymin']), (item['xmax'], item['ymax']), (255, 255, 255), 3)
        label_str = str(item['label'])
        if "score" in item.keys():
            label_str += ' ' + str(round(100*item["score"], 2)) + '%'
        cv2.putText(img=image,
                    text=label_str,
                    org=(item['xmin'], item['ymin']),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=.8e-3 * image.shape[0],
                    color=(0,0,0),
                    thickness=2)
    if save:
        filepath, extension = os.path.splitext(image_file)
        cv2.imwrite(filepath + '_annotated' +extension, image)
    else:
        # Get screen reolution, it's a reasonable bet that everyone should have Tkinter
        root = Tkinter.Tk()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy()
        # Check if our image is larger than screen in any dimension
        im_width = image.shape[0]
        im_height = image.shape[1]
        ratio = min( (float(width) / im_width) , (float(height) / im_height) )
        if ratio < 1:
            image = cv2.resize(image, ( int(ratio * im_width), int(ratio * im_height)))
        cv2.imshow(image_filename, image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

def crop_image(image_file, voc_file, x, y, width, height, output_directory, output_filename=None):
    '''
    crop_image(image_file, voc_file, x, y, width, height, output_directory, output_filename=None)
    Crops the image file defined in the passed "voc_file", expected to be in
    PASCAL VOC xml format, generated by method "generate_VOC_annotations".
    The cropped image has top left at passed "x", "y" and dimensions of passed
    "width", "height". If the image is not large enough for either width or
    height, it is cropped up to its maximum dimensions.
    The resulting cropped image and its associated annotations file in PASCAL
    VOC xml format are saved in passed "output_directory".
    If "output_filename" has been supplied, it overrides the filename of the input.
    NOTE: supplied "output_filename" should NOT include exentions as the original file extension
    will be used.
    If "output_filename" has not been supplied, the original is used with '_cropped' attached.
    '''
    if not os.access(output_directory,  os.W_OK):   # check output dir exists and we can write to it
        print("Error: cannot write to directory: " + output_directory)
        return
    data = parse_VOC(voc_file)
    image_name, extension = os.path.splitext(os.path.basename(image_file))
    if output_filename is not None:
        out_name = output_filename
    else:
        out_name = image_name + '_cropped'
    output_image_filepath = os.path.join(output_directory, out_name + extension)
    output_annot_filepath = os.path.join(output_directory, out_name + '.xml')
    if os.path.isfile(output_image_filepath):
        print("Error: file already exists: " + output_image_filepath)
        return
    if os.path.isfile(output_annot_filepath):
        print("Error: file already exists: " + output_annot_filepath)
        return
    # Reaching here means we have done our file and path tests and we are OK to write our outputs
    # First we do the image file
    image = Image.open(image_file)
    x2 = min(image.width, x+width)
    y2 = min(image.height, y+height)
    imc=image.crop((x, y, x2, y2))
    imc.save(output_image_filepath, quality=95)
    print('Saved image: ' + output_image_filepath)
    # Then we do the annotation file
    writer = Writer(output_image_filepath, imc.width, imc.height)
    for shape in data['shapes']:
        xmin = shape['xmin'] - x
        xmax = shape['xmax'] - x
        ymin = shape['ymin'] - y
        ymax = shape['ymax'] - y
        if xmin < 0 or xmin > width:
            continue
        if ymin < 0 or ymin > height:
            continue
        if xmax < 0 or xmax > width:
            continue
        if ymax < 0 or ymax > height:
            continue
        writer.addObject(shape['label'], xmin, ymin, xmax, ymax)
    writer.save(output_annot_filepath)
    print("Saved annotation file: " + output_annot_filepath)

def get_image_ROI(voc_file):
    '''
    Given passed annotation file "voc_file", expected to be in PASCAL VOC xml
    format, generated by method "generate_VOC_annotations", gets the
    "bounding box of bounding boxes", i.e. the outer limits of tagged items in
    the image in format: [[xmin, ymin], [xmax, ymax]]
    '''
    data = parse_VOC(voc_file)
    if not data['shapes']:
        return None
    xmax = data['shapes'][0]['xmax']
    ymax = data['shapes'][0]['ymax']
    xmin = data['shapes'][0]['xmin']
    ymin = data['shapes'][0]['ymin']
    for shape in data['shapes']:
            xmax = max(shape['xmax'], xmax)
            xmin = min(shape['xmin'], xmin)
            ymax = max(shape['ymax'], ymax)
            ymin = min(shape['ymin'], ymin)
    return {'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax}

def get_sliced_shapes(data, coord_type, coord_value, opposite_range = None):
    '''
    Returns a list of shapes from passed "data" which will be sliced
    through if a line passes through "coord_value".
    "data" is the dict returned by parsing a VOC xml file via
    "parse_VOC(voc_file)"
    "coord_type" has to be defined as either 'x' for a vertical
    line or 'y' for horizontal line.
    If tuple "opposite_range" is passed, only shapes lying wholy or
    partially in that range of the OPPOSITE coordinate are returned.
    For example, say:
    coord_type = 'x'
    coord_value = 100
    and this slices two objects whose ymin, ymax coords are
    (10, 100) and (250, 320)
    If opposite_range is (50, 200), the first item will be returned (partially
    lies in the range) but not the second.
    '''
    if not (coord_type is 'x' or coord_type is 'y'):
        print('Error: coord_type has to be either \'x\' or \'y\'')
        return None
    sliced_shapes = []
    for shape in data['shapes']:
        if coord_type is 'x':
            if ((shape['xmin'] <= coord_value and shape['xmax'] >= coord_value)) and (opposite_range is None or (opposite_range is not None and shape['ymin'] <= max(opposite_range) and shape['ymax'] >= min(opposite_range))):
                sliced_shapes.append(shape)
        elif coord_type is 'y':
            if ((shape['ymin'] <= coord_value and shape['ymax'] >= coord_value)) and (opposite_range is None or (opposite_range is not None and shape['xmin'] <= max(opposite_range) and shape['xmax'] >= min(opposite_range))):
                sliced_shapes.append(shape)
    return sliced_shapes

def get_safe_crop_boundaries(data, x, y, width, height):
    '''
    Returns crop boundaries which will not slice through any shapes identified
    in passed "data", which is the dict returned by parsing a VOC xml file via
    "parse_VOC(voc_file)". The desired, initial crop boundaries are in passed
    "x", "y" (top left) and "width", "height".
    The crop lines are continuously pushed towards smaller images (towards the
    centre of the crop area) until they do not slice any shapes. If no safe crop
    boundaries are possible, None is returned.
    '''
    # Left slice: new x origin, xnew
    xnew = x
    sliced = get_sliced_shapes(data, 'x', xnew, opposite_range=(y, y + height))
    while sliced:  # sliced returns empty (False) if nothing is sliced
        # find the rightmost coordinate among the sliced shapes
        xnew = max([d['xmax'] for d in sliced]) + 1
        if xnew >= x + width:
            return None
        sliced = get_sliced_shapes(data, 'x', xnew, opposite_range=(y, y + height))

    # Top slice: new y origin, ynew
    ynew = y
    sliced = get_sliced_shapes(data, 'y', ynew, opposite_range=(xnew, x + width))
    while sliced:  # sliced returns empty (False) if nothing is sliced
        # find the rightmost coordinate among the sliced shapes
        ynew = max([d['ymax'] for d in sliced]) + 1
        if ynew >= y + height:
            return None
        sliced = get_sliced_shapes(data, 'y', ynew, opposite_range=(xnew, x + width))

    # Right slice: new width, found via new x rightmost position, xmax
    xmax = x + width
    sliced = get_sliced_shapes(data, 'x', xmax, opposite_range=(ynew, y + height))
    while sliced:  # sliced returns empty (False) if nothing is sliced
        # find the rightmost coordinate among the sliced shapes
        xmax = min([d['xmin'] for d in sliced]) - 1
        if xmax <= xnew:
            return None
        sliced = get_sliced_shapes(data, 'x', xmax, opposite_range=(ynew, y + height))
    width_new = xmax - xnew

    # Bottom slice: new height, found via new y bottom most position, ymax
    ymax = y + height
    sliced = get_sliced_shapes(data, 'y', ymax, opposite_range=(xnew, xmax))
    while sliced:  # sliced returns empty (False) if nothing is sliced
        # find the rightmost coordinate among the sliced shapes
        ymax = min([d['ymin'] for d in sliced]) - 1
        if ymax <= ynew:
            return None
        sliced = get_sliced_shapes(data, 'y', ymax, opposite_range=(xnew, xmax))
    height_new = ymax - ynew

    return {'x': xnew, 'y': ynew, 'width': width_new, 'height': height_new}


def slice_to_tiles(image_file, tile_width, tile_height, output_directory, annotation_file=None):
    '''
    Slices "image_file" into tiles such that there will be as many
    tiles as needed to cover the whole image with some overlap
    given dimensions "tile_width" and "tile_height", e.g.
    number of horizontal tiles = 1 + (image width / tile width)
    The tiles might end up smaller than the passed values since
    the slicing avoids cutting through shapes as described in the
    image's corresponding annotation file, see function
    "get_safe_crop_boundaries" which this function calls.

    The results are saved in "output_directory" with filenames
    based on the original and _x-y added depending on the tile.
    For example, the tile on the zeroth row, third column of
    image file "IMAGE.JPG" will be saved as "IMAGE_0-3.JPG"
    
    If no "annotation_file" is passed, the function will look
    for one with the same base name and .xml extension in the
    same directory as the image file, "IMAGE.xml" in the example
    above.
    '''
    if not os.path.isfile(image_file):
        print('File does not exist: ' + image_file)
        return None
    if annotation_file is not None:
        voc_file = annotation_file
    else:
        voc_file = os.path.splitext(image_file)[0] + '.xml'
    if not os.path.isfile(voc_file):
        print('The xml VOC file associated with this image does not exist: ' + voc_file)
        return None
    if not os.path.isdir(output_directory):
        os.mkdir(output_directory)

    data = parse_VOC(voc_file)
    height, width = (cv2.imread(image_file)).shape[0:2]
    horizontal_tiles = int((width / tile_width) + 1)
    vertical_tiles = int((height / tile_height) + 1)
    if horizontal_tiles > 1:
        horizontal_step = int((width - tile_width) / (horizontal_tiles - 1))
    else:
        horizontal_step = 0
    if vertical_tiles > 1:
        vertical_step = int((height - tile_height) / (vertical_tiles - 1))
    else:
        vertical_step = 0

    for h in range(horizontal_tiles):
        for v in range(vertical_tiles):
            cb = get_safe_crop_boundaries(
                data, h*horizontal_step, v*vertical_step, tile_width, tile_height)
            if not contains_items(data, cb['x'], cb['y'], cb['width'], cb['height']):
                continue
            outname = os.path.splitext(os.path.basename(image_file))[
                0] + '_' + str(h) + '-' + str(v)
            crop_image(image_file, voc_file, cb['x'], cb['y'], cb['width'], cb['height'],
                       output_directory, output_filename=outname)


def contains_items(data, x, y, width, height):
    '''
    Returns True of the region of image whose contents are stored
    in "data" (the dict returned by parsing a VOC xml file via
    "parse_VOC(voc_file)") contains any shapes. For the return to
    be true, the shape must lie wholy within the region, not sliced
    by any of its boundaries.    
    '''
    for shape in data['shapes']:
        if (x <= shape['xmin'] <= (x + width)) and (x <= shape['xmax'] <= (x + width)) and (y <= shape['ymin'] <= y + height) and (y <= shape['ymax'] <= y + height):
            return True
    return False
    

def get_labels(annotation_dir):
    '''
    Returns a list of the labels seen in the annotation files of
    passed "annotation_directory"
    '''
    labels = set()
    filelist = os.listdir(annotation_dir)
    for file in filelist:
        if file.endswith('xml'):
            data = parse_VOC(os.path.join(annotation_dir, file))
            for shape in data['shapes']:
                labels.add(shape['label'])
    return list(labels)


def dataset_crop_to_ROI(dataset_path, output_directory, roi_padding = 10):

    filelist = os.listdir(dataset_path)
    imagelist = []
    for file in filelist:
        if file.endswith('JPG'):
            imagelist.append(file)

    for image in imagelist:
        image_path = os.path.join(dataset_path, image)
        annotation_path = os.path.join(dataset_path, image[0:image.find('.JPG')] + '.xml')
        if not os.path.isfile(annotation_path):
            print('No annotations file found for image file: ' + str(image) + '. Skipping.')

        roi = get_image_ROI(annotation_path)
        if roi is None:
            continue

        if not os.path.isdir(output_directory):
            os.mkdir(output_directory)

        crop_image(image_path, annotation_path, max(0, roi['xmin'] - roi_padding), max(0, roi['ymin'] - roi_padding), roi['xmax'] - roi['xmin'] + 2*roi_padding,
                   roi['ymax'] - roi['ymin'] + 2*roi_padding, output_directory, output_filename=os.path.splitext(os.path.basename(image_path))[0] + '_ROIcrop')


def dataset_to_tiles(dataset_path, tile_width, tile_height, output_directory):

    filelist = os.listdir(dataset_path)
    imagelist = []
    for file in filelist:
        if file.endswith('JPG'):
            imagelist.append(file)
    
    for image in imagelist:
        image_path = os.path.join(dataset_path, image)
        slice_to_tiles(image_path, tile_width, tile_height,
                       output_directory)


def display_image(input_image, height=1000):
    '''
    Quick and dirty image viewer.
    Args:
        input_image: an image, as numpy array as loaded by cv2.imread()
        height: desired height in pixels, default 1000. If set to 0, no scaling will be applied
    '''
    dims = input_image.shape
    if height == 0:
        scale = 1.0
    else:
        scale = float(height) / float(dims[0])
    im_scaled = cv2.resize(
        input_image, (int(scale * dims[1]), int(scale * dims[0])))
    # make sure we cast to uint8 so we can handle other dtypes gracefully
    cv2.imshow('image', im_scaled.astype(np.uint8))
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def create_minimal_image(input_image_path, out_image_path, threshold=50):
    '''
    Takes an input image of an item and saves an image cropped to the item's bounding box
    and all non-item space filled with transparency.
    The input image is expected to only contain the item against a background as black as possible.
    The idea is that the resulting image can be pasted into any arbitrary image to create a composite
    containing the item.
    Args:
        input_image_path: path to the input image.
        out_image_path: path to the image to save as output. The result will be a PNG with transparency.
        threshold: threshold to filter black / white values once input has been converted to grayscale.
    Returns:
        True for successful saving of the output image, False otherwise.
    '''

    # Get the input
    input_image = cv2.imread(input_image_path)
    if input_image is None:
        return False

    # Convert to grayscale
    img = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)

    # Convert to binary via a hard cutoff
    img[np.where(img >= threshold)] = 255
    img[np.where(img < threshold)] = 0

    # Grab the biggest item (hopefully our item), in case more items slipped through the BW conversion
    img = select_largest_obj(img, fill_holes = False)
    
    # Add our mask as an alpha channel to the original image
    b, g, r = cv2.split(input_image)
    out_img = cv2.merge((b, g, r, img))

    # Crop the image
    cnt = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # get contours from the mask
    x, y, w, h = cv2.boundingRect(cnt[1][0])   # get the (straight) bounding rectangle
    out_img = out_img[y:y+h, x:x+w]            # crop the whole image

    # Write out the result
    ext = os.path.splitext(out_image_path)[1]
    if not ext == '.png' or ext == '.PNG':
        out_image_path += '.png'
    if os.path.isfile(out_image_path):
        print('Error: output file already exists')
    cv2.imwrite(out_image_path, out_img)


def scale_minimal_image(input_image_path, longest_dim_pixels, resize_mode='INTER_AREA'):
    '''Rescales a minimal image, i.e. a PNG with alpha channel of a litter item as created by 
    "create_minimal_image()", so that its longest dimension in pixels is equal to "longest_dim_pixels".
    Args:
        input_image_path: path to the input image.
        longest_dim_pixels: desired length in pixels of the longest dimension in the output image
        resize_mode (optional, default 'INTER_AREA'): code for the interpolation method as described in:
            https://docs.opencv.org/2.4/modules/imgproc/doc/geometric_transformations.html#resize
        Possible values are:
            INTER_NEAREST - a nearest-neighbor interpolation
            INTER_LINEAR - a bilinear interpolation (used by default)
            INTER_AREA - resampling using pixel area relation.
            INTER_CUBIC - a bicubic interpolation over 4x4 pixel neighborhood
            INTER_LANCZOS4 - a Lanczos interpolation over 8x8 pixel neighborhood
    Returns:
        The scaled 4 channel image
    ''' 
    img = cv2.imread(input_image_path, cv2.IMREAD_UNCHANGED)
    dims = img.shape
    scale = float(longest_dim_pixels) / max(dims)
    new_width = int(dims[1] * scale)
    new_height = int(dims[0] * scale)

    if resize_mode == 'INTER_NEAREST':
        interpolation = cv2.INTER_NEAREST
    elif resize_mode == 'INTER_LINEAR':
        interpolation = cv2.INTER_LINEAR
    elif resize_mode == 'INTER_AREA':
        interpolation = cv2.INTER_AREA
    elif resize_mode == 'INTER_CUBIC':
        interpolation = cv2.INTER_CUBIC
    elif resize_mode == 'INTER_LANCZOS4':
        interpolation = cv2.INTER_LANCZOS4
    else:
        print("Error, resize_mode: " + str(resize_mode) + " not recognised.\nValid modes are:\nINTER_NEAREST\nINTER_LINEAR\nINTER_AREA\nINTER_CUBIC\nINTER_LANCZOS4")
        return False

    # resize the image
    out_img = cv2.resize(
        img, (new_width, new_height), interpolation=interpolation)
    
    return out_img


def rotate_bound(image, angle):
    '''
    Copied from Adrian Rosebrock's code at:
    https://www.pyimagesearch.com/2017/01/02/rotate-images-correctly-with-opencv-and-python/
    '''
    # grab the dimensions of the image and then determine the
    # center
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)

    # grab the rotation matrix (applying the negative of the
    # angle to rotate clockwise), then grab the sine and cosine
    # (i.e., the rotation components of the matrix)
    M = cv2.getRotationMatrix2D((cX, cY), -angle, 1.0)
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])

    # compute the new bounding dimensions of the image
    nW = int((h * sin) + (w * cos))
    nH = int((h * cos) + (w * sin))

    # adjust the rotation matrix to take into account translation
    M[0, 2] += (nW / 2) - cX
    M[1, 2] += (nH / 2) - cY

    # perform the actual rotation and return the image
    return cv2.warpAffine(image, M, (nW, nH))


def blend_alpha_image(min_img, back_img, x, y):
    '''
    Loosely based on the following tutorial by Sunita Nayak:
    https://www.learnopencv.com/tag/alpha-blending/
    Pastes an image with alpha channel into a larger background image and returns the result.
    The idea is that images with transparent backgrounds will be pasted into background images at known locations to be used for training neural networks.
    Args:
        min_img: the smaller image with alpha channel. This can be loaded via scale_minimal_image() and possibly further rotated via rotate_bound() before being passed to blend_alpha_image().
        back_img: a background image, which has to be larger than the the minimal image
        x, y: coords for the top right corner location in the background image to paste the minimal image
    Returns:
        (image, (xmin, ymin, xmax, ymax)) where image is the resulting blended image and (xmin, ymin, xmax, ymax) are the coordinates of the bounding box of the pasted minimal image.
        If the pasting location is such that the minimal image does not fit, returns None.
    '''
    # Make the mask, foreground and background slice where we will paste
    r, g, b, alpha = cv2.split(min_img)
    foreground = cv2.merge((r, g, b))
    min_dims = min_img.shape
    back_dims = back_img.shape
    if (y + min_dims[0] > back_dims[0]) or (x + min_dims[1] > back_dims[1]):  # check that we are not dropping off the edges of the background image
        print('Error in blend_alpha_image(): blending images with required foreground params would result in image beyond edges of background. Returning None.')
        return None
    background = back_img[y:y + min_dims[0], x:x + min_dims[1]]

    # Cast all into appropriate types
    foreground = foreground.astype(float)
    background = background.astype(float)

    # Convert alpha to 0-1 range
    alpha = alpha.astype(float) / 255

    # Apply mask and blend fg and bg
    background = cv2.merge((cv2.multiply(1.0 - alpha, cv2.split(background)[0]), cv2.multiply(
        1.0 - alpha, cv2.split(background)[1]), cv2.multiply(1.0 - alpha, cv2.split(background)[2])))
    foreground = cv2.merge((cv2.multiply(alpha, cv2.split(foreground)[0]), cv2.multiply(
        alpha, cv2.split(foreground)[1]), cv2.multiply(alpha, cv2.split(foreground)[2])))
    blend = cv2.add(foreground, background)

    # Paste the edited slice into the larger background image
    back_img[y:y + min_dims[0], x:x + min_dims[1]] = blend

    return back_img, (x, y, x + min_dims[1], y + min_dims[0])

def create_composite_image(min_img_dict, background_image, output_image_path, output_annotation_path=None):
    '''
    Creates a composite image of multiple minimal images pasted against a background image. The idea is to create images of items at known locations in order to train neural networks.
    The minimal images are 4 channel PNGs with alpha channel as created by create_minimal_image() and are passed as a list of dictionaries containing information about where and how to paste them.
    The background image is expected to be an image of a suitable background for training the neural networks.
    Args:
        min_img_dict: a list of dictionaries, each of which has to contain the following keys:
            path: path to the minimal image. This has to be PNG with alpha channel (4 channel)
            label: label of the item depicted in the minimal image
            longest_dimension: longest dimension of the minimal image after scaling as described in "scale_minimal_image()"
            rotation_angle: angle to rotate the minimal image as described in "rotate_bound()"
            x, y: location in background image to paste top right corner of minimal image
            resize_mode: OPTIONAL key, if present, works as described in "scale_minimal_image()".
        background_image: either a path to the background image or an image object as loaded by cv2.imread().
        output_image_path: path to save resulting composite
        output_annotation_path: OPTIONAL path for the annotation file in PASCAL VOC format. If missing, it will be created with the same base filename as "output_image_path" but with an .xml extension.
    Returns:
        If the all goes well and output files can be written into, rerturns the composite image as an object. Otherwise, the results are NOT saved and returns False.
    '''
    # Grab our background image
    if isinstance(background_image, np.ndarray):
        back_img = background_image
    elif isinstance(background_image, str):
        if os.path.isfile(background_image):
            back_img = cv2.imread(background_image, cv2.IMREAD_UNCHANGED)
        else:
            print('Error: argument background_image does not point to a valid image file.')
    else:
        print('Error: argument background_image has to be either a path to an image file or be an image object (numpy.ndarray)')
        return False

    # Create a writer object for the annotation file
    writer = Writer(output_image_path, back_img.shape[1], back_img.shape[0])

    # Paste the list of minimal images in the background image
    for im in min_img_dict:
        if 'resize_mode' in im:
            min_img = scale_minimal_image(im['path'], im['longest_dimension'], resize_mode=im['resize_mode'])
        else:
            min_img = scale_minimal_image(im['path'], im['longest_dimension'])
        min_img = rotate_bound(min_img, im['rotation_angle'])
        try:
            back_img, bounding_box = blend_alpha_image(min_img, back_img, im['x'], im['y'])
        except:     # blending that would paste foreground beyond egdes of background returns None...
            return False    # ...in which case, we just exit with False
        
        writer.addObject(im['label'], bounding_box[0], bounding_box[1], bounding_box[2], bounding_box[3])

    if output_annotation_path is None:
        output_annotation_path = os.path.splitext(output_image_path)[0] + '.xml'

    # Write out the resulting image
    if os.path.isfile(output_image_path):
        print('Error: output image file already exists')
        return False
    # Write out the annotation file
    if os.path.isfile(output_annotation_path):
        print('Error: output annotation file already exists')
        return False
    cv2.imwrite(output_image_path, back_img)
    writer.save(output_annotation_path)
    return back_img


def generate_random_pasted_set(label, longest_dimension, min_image_dir, background_image_dir, output_directory, number_of_output_images, max_items_per_image, output_width_pixels=500, output_height_pixels=500, randomise_resize_mode=True):
    
    # Parse the input directories for valid file types
    background_files = [i for i in os.listdir(background_image_dir) if ((os.path.splitext(i)[1]).lower() == '.jpg' or (os.path.splitext(i)[1]).lower() == '.png')]
    min_image_files = [i for i in os.listdir(min_image_dir) if ((os.path.splitext(i)[1]).lower() == '.jpg' or (os.path.splitext(i)[1]).lower() == '.png')]

    for i in range(number_of_output_images):
        # Grab a random background image
        back_path = os.path.join(
            background_image_dir, background_files[random.randint(0, len(background_files) - 1)])
        back_img = cv2.imread(back_path, cv2.IMREAD_UNCHANGED)

        # Grab a random piece of the the background image of max dimensions output_width_pixels x output_height_pixels
        dims = back_img.shape
        x0 = 0
        y0 = 0
        if dims[0] > output_height_pixels:
            y0 = random.randint(0, dims[0] - output_height_pixels)
        if dims[1] > output_width_pixels:
            x0 = random.randint(0, dims[1] - output_width_pixels)
        back_img = back_img[y0: y0+output_height_pixels,
                            x0: x0+output_width_pixels]

        # Make a list of dictionaries as needed for function create_composite_image()
        min_img_dict = []
        # Note: we will produce a random number of dict entries between 1 and "max_items_per_image"
        for j in range(random.randint(1, max_items_per_image)):
            dims = back_img.shape
            d = {}
            d['path'] = os.path.join(min_image_dir, min_image_files[random.randint(
                0, len(min_image_files) - 1)])  # get a path to a random min image
            d['label'] = label
            d['longest_dimension'] = longest_dimension
            d['rotation_angle'] = random.randint(0, 359)
            d['y'] = random.randint(0, dims[0] - longest_dimension)
            d['x'] = random.randint(0, dims[1] - longest_dimension)
            if randomise_resize_mode:
                d['resize_mode'] = random.sample(
                    ['INTER_NEAREST', 'INTER_LINEAR', 'INTER_AREA', 'INTER_CUBIC', 'INTER_LANCZOS4'], 1)[0]
            min_img_dict.append(d)

        output_image_path = os.path.join(output_directory, 'composite_' + str(i) + '.jpg')
        create_composite_image(min_img_dict, back_img,output_image_path)
