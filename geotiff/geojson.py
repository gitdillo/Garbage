import geotiff

def newCollection():
    return {
        "type": "FeatureCollection",
        "features": []
    }

def addFeatureFromBoundingBox(geojson, ds, bbox, properties = {}):
    gt = ds.GetGeoTransform()

    cols = ds.RasterXSize
    rows = ds.RasterYSize

    coords = geotiff.GetCoordinatesFromPixelBox(
        gt,
        cols,
        rows,
        bbox["x"],
        bbox["y"],
        bbox["width"],
        bbox["height"],
    )

    topLeft     = [coords[0], coords[1]]
    topRight    = [coords[2], coords[1]]
    bottomLeft  = [coords[0], coords[3]]
    bottomRight = [coords[2], coords[3]]

    geojson["features"].append({
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    topLeft,
                    topRight,
                    bottomRight,
                    bottomLeft
                ]
            ]
        },

        "properties": properties
    })

    return [topLeft, topRight, bottomRight, bottomLeft]
