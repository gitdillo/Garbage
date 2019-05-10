from decimal import Decimal
from osgeo import gdal, ogr, osr

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

    gt = map(Decimal, gt)

    xarr = map(Decimal, [0, cols])
    yarr = map(Decimal, [0, rows])

    for px in xarr:
        for py in yarr:
            x = gt[0] + (px * gt[1]) + (py * gt[2])
            y = gt[3] + (px * gt[4]) + (py * gt[5])

            ext.append([x, y])

        yarr.reverse()

    return ext

def GetCoordinatesFromPixelBox(gt, cols, rows, x, y, width, height):
    ext = GetExtent(gt, cols, rows)

    cols, rows, x, y = map(Decimal, [cols, rows, x, y])

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

