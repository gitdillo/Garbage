import Metashape
import json


output_file = 'C:/Users/x/Desktop/polygons.json'


def model2pixel(point, camera, chunk):
	""" Converts the coordinates of passed point from model coordinates to camera (pixel) coordinates for the passed camera and chunk. """
	T = chunk.transform.matrix #4x4 transformation matrix
	point_geocentric = chunk.crs.unproject(point) #points in geocentric coordinates
	point_internal = T.inv().mulp(point_geocentric)
	point_2D = camera.project(point_internal) #2D image coordinates for the point
	pixel_coords = [round(point_2D[0]), round(point_2D[1])]
	return pixel_coords



def shape2image(shape, camera, chunk):
	"""
	Converts model coordinates of passed shape to image coordinates of passed camera and chunk.
	If the shape does not lie completely in the camera image, returns None.
	"""
	image_coords = list()
	for vertex in shape.vertices:
		pixel_coords = model2pixel(vertex, camera, chunk)
		if pixel_coords[0] > camera.sensor.width or pixel_coords[0] < 0 or pixel_coords[1] > camera.sensor.height or pixel_coords[1] < 0:  # check coords lie inside image
			return None
		image_coords.append(pixel_coords)
	return image_coords


def get_all_shapes_in_camera(camera, chunk):
	""" Returns a list of lists.
	Each list contains coordinates in image (pixel) coordinates of a shape.
	Every shape in the chunk that is completely inside the camera's image is in the list.
	"""
	pixel_shapes = list()	# list to hold the shapes in pixel coords
	for shape in chunk.shapes:
		ps = shape2image(shape, camera, chunk)
		if ps is not None:
			pixel_shapes.append({"label": shape.label, "vertices": ps})
	return pixel_shapes


chunk = PhotoScan.app.document.chunk
image_data = list()
for i in range(len(chunk.cameras)):
	if not chunk.cameras[i].enabled:
		continue
	image_data.append({"image": chunk.cameras[i].label, "shapes": get_all_shapes_in_camera(chunk.cameras[i], chunk)})


with open(output_file, 'w') as f:
	json.dump(image_data, f, indent=4, sort_keys=True)

print("Polygons saved in file: " + output_file)