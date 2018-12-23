from pascal_voc_writer import Writer
from PIL import Image, ImageDraw, ImageFont
import json
import os
import xml.etree.ElementTree as ET
import cv2
import Tkinter
import pdb

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
                    fontScale=.4e-3 * image.shape[0],
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
    image = Image.open(data['path'])
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
    horizontal_tiles = (width / tile_width) + 1
    vertical_tiles = (height / tile_height) + 1
    horizontal_step = (width - tile_width) / (horizontal_tiles - 1)
    vertical_step = (height - tile_height) / (vertical_tiles - 1)

    for h in range(horizontal_tiles):
        for v in range(vertical_tiles):
            cb = get_safe_crop_boundaries(
                data, h*horizontal_step, v*vertical_step, tile_width, tile_height)
            outname = os.path.splitext(os.path.basename(image_file))[
                0] + '_' + str(h) + '-' + str(v)
            crop_image(image_file, voc_file, cb['x'], cb['y'], cb['width'], cb['height'],
                       output_directory, output_filename=outname)


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


