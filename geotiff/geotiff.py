from decimal import Decimal
from osgeo import gdal, ogr, osr
import math
from collections import namedtuple

class MemImage:
    path        = None
    coordsPath  = None
    invalidated = False

    def __init__(self, path, coordsPath):
        self.path       = path
        self.coordsPath = coordsPath

    def getPath(self):
        if self.invalidated:
            raise Exception("Mem image index has been replaced.")

        return self.path

    def invalidate(self):
        self.invalidated = True

def SliceDatasetToFile(ds, output, x, y, width, height):
    driver = gdal.GetDriverByName("GTiff")
    dst_ds = driver.Create(output, 
       width, 
       height, 
       ds.RasterCount, 
       gdal.GDT_Float32
    )

    f = WriteChunkedGTiff(ds, dst_ds, x, y, width, height)

    # Some hack, doesn't leave translation empty if using returned dataset.
    f.ReadAsArray()
    f.FlushCache()

    return f

def SliceDataset(ds, x, y, width, height):
    driver = gdal.GetDriverByName("MEM")
    dst_ds = driver.Create("", 
       width, 
       height, 
       ds.RasterCount, 
       gdal.GDT_Float32
    )

    return WriteChunkedGTiff(ds, dst_ds, x, y, width, height)

def GetCoords(ds):
    geo = ds.GetGeoTransform()

    originX = geo[0]
    originY = geo[3]

    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjection())

    srsLatLong = srs.CloneGeogCS()
    ct = osr.CoordinateTransformation(srs, srsLatLong)

    return ct.TransformPoint(originX, originY)

def DatasetToJPEG(ds, output = None):
    coords = GetCoords(ds)
    memImage = GTifToJPEG(ds, 3, output)

    return (memImage, coords)

memoLimit = 10
memo = {
    "at": 0,
    "list": [None] * memoLimit
}
def GTifToJPEG(tif, bandCount, output = None):
    options = [
        "-ot Byte",
        "-of PNG",
    ]

    for bandIdx in range(1, bandCount + 1):
        options.append("-b {0}".format(bandIdx))

    if (output == None):
        idx = memo["at"] % memoLimit

        output = "/vsimem/inmemjpeg{0}.jpg".format(idx)
        memImage = MemImage(output, output + ".aux.xml")

        memo["list"][idx] = memImage
        memo["at"] = (idx + 1) % memoLimit
        prevImage = memo["list"][memo["at"]]
        if prevImage is not None:
            prevImage.invalidate()
    else:
        memImage = MemImage(output, output + ".aux.xml")

    gdal.Translate(output, tif, options = " ".join(options))
    return memImage

def WriteChunkedGTiff(ds, dst_ds, x, y, width, height):
    gt = ds.GetGeoTransform()
    cols = ds.RasterXSize
    rows = ds.RasterYSize

    # Write all raster layers to new file
    for bandIdx in range(1, ds.RasterCount + 1):
        band = ds.GetRasterBand(bandIdx)
        data = band.ReadAsArray(x, y, width, height)
        dst_ds.GetRasterBand(bandIdx).WriteArray(data)

    coords = GetCoordinatesFromPixelBox(gt, cols, rows, x, y, width, height)

    # top left x, w-e pixel resolution, rotation, top left y, rotation, n-s pixel resolution
    new_transformation = [coords[0], gt[1], gt[2], coords[1], gt[4], gt[5]]
    dst_ds.SetGeoTransform(new_transformation)

    wkt = ds.GetProjection()

    # setting spatial reference of output raster 
    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt)
    dst_ds.SetProjection( srs.ExportToWkt() )

    return dst_ds

def GetExtent(gt, cols, rows):
    ext=[]

    gt = amap(Decimal, gt)

    xarr = amap(Decimal, [0, cols])
    yarr = amap(Decimal, [0, rows])

    for px in xarr:
        for py in yarr:
            x = gt[0] + (px * gt[1]) + (py * gt[2])
            y = gt[3] + (px * gt[4]) + (py * gt[5])

            ext.append([x, y])

        yarr.reverse()

    return ext

def GetCoordinatesFromPixelBox(gt, cols, rows, x, y, width, height):
    ext = GetExtent(gt, cols, rows)

    cols, rows, x, y = amap(Decimal, [cols, rows, x, y])

    xOrigin = Decimal(gt[0])
    yOrigin = Decimal(gt[3])

    bottomLeft, topLeft, topRight, bottomRight = ext
    xlen = Decimal(topRight[0]) - Decimal(topLeft[0])
    ylen = Decimal(bottomRight[1]) - Decimal(topRight[1])

    # Notice the negative leap with regards to Y.
    return [
        xOrigin + (x / cols) * xlen,
        yOrigin - (y / rows) * ylen,
        xOrigin + ((x + width) / cols) * xlen,
        yOrigin - ((y + height) / rows) * ylen,
    ]


Box = namedtuple("Box", ["xmin", "ymin", "xmax", "ymax", "score"])
def getPixelBoxesFromShapes(ds, shapes, score = None):
    cols = ds.RasterXSize
    rows = ds.RasterYSize

    gt = ds.GetGeoTransform()

    ext = GetExtent(gt, cols, rows)

    xOrigin = Decimal(gt[0])
    yOrigin = Decimal(gt[3])

    bottomLeft, topLeft, topRight, bottomRight = ext
    xlen = Decimal(topRight[0]) - Decimal(topLeft[0])
    ylen = Decimal(bottomRight[1]) - Decimal(topRight[1])

    parsed = []
    for shape in shapes:
        xmin = False
        ymin = False
        xmax = False
        ymax = False

        for coords in shape:
            lon, lat = amap(Decimal, coords)

            x = (lon - xOrigin) / xlen * cols
            y = (yOrigin - lat) / ylen * rows

            xmin = x if not xmin or x < xmin else xmin
            ymin = y if not ymin or y < ymin else ymin

            xmax = x if not xmax or x > xmax else xmax
            ymax = y if not ymin or y > ymax else ymax

        parsed.append(Box(
            xmin = int(xmin),
            ymin = int(ymin),
            xmax = int(xmax),
            ymax = int(ymax),
            score = score
        ))

    return parsed

def amap(f, l):
    return list(map(f, l))

def LoopSlices(
    ds, sliceSize, overlap, callback,
    startX = 0, startY = 0, maxX = None, maxY = None
):
    rasterX = ds.RasterXSize
    rasterY = ds.RasterYSize

    yCeil = int(math.ceil(rasterY / sliceSize))
    xCeil = int(math.ceil(rasterX / sliceSize))

    yAmount = 0
    xAmount = 0

    for y in range(startY, yCeil):
        if maxY != None and maxY <= yAmount:
            break

        ys = zeroNegatives(y * sliceSize - overlap)
        my = 1 if y == 0 else 2

        yAmount = yAmount + 1
        xAmount = 0

        for x in range(startX, xCeil):
            if maxX != None and maxX <= xAmount:
                break

            xs = zeroNegatives(x * sliceSize - overlap)

            mx = 1 if x == 0 else 2
            
            w = limit(rasterX, xs, sliceSize + mx * overlap)
            h = limit(rasterY, ys, sliceSize + my * overlap)
            
            m = SliceDataset(
                ds,
                xs,
                ys,
                w,
                h
            )

            xAmount = xAmount + 1
            callback(m, xs, ys, w, h)

def limit(upper, at, value):
    return upper - at if at + value > upper else value

def zeroNegatives(v):
    return 0 if v < 0 else v
