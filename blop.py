import os
import json

polypath = '/windows_storage/IT/Keras_YOLO/litter_data/Training_Data/Radanvagen_set_6-7_Dec_2019/'

dirs = os.listdir(polypath)

tallies = []
for dir in dirs:
  if not os.path.isdir(polypath + dir):
    continue
  with open(polypath + dir + '/polygons.json', 'r') as f:
    tally = 0
    polys = json.load(f)
    for image in polys:
      tally += len(image['shapes'])
    print(str(tally) + ' items in file ' + f.name)
    tallies.append(tally)

print('Total: ' + str(sum(tallies)))
