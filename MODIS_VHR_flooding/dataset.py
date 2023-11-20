import argparse
import os
import csv
import pandas as pd
from osgeo import gdal, ogr, osr
import georasters as gr
import geopandas as gpd
from shapely.geometry import box
import ee
import modis_toolbox as mod_tol
import pyproj
import geemap
import re
import datetime
import numpy as np
# os.environ['HTTP_PROXY'] = r'http://127.0.0.1:7890'
# os.environ['HTTPS_PROXY'] = r'https://127.0.0.1:7890'
# os.environ['PROJ_LIB'] = r'./osgeo/data/proj'



'''
There are three types of images: MODIS (pre and post), VHR (pre and post), and masks for flooded road and buildings.
The three types of data should be matched with each other in one same region. Now I set the image size as 2 km. The output of this module should include a series of images with the information of the relation between the three different types of images.

### Input
The image size
The geographical location of the images (can be extracted from VHR and flooded mask)

### Output
A .csv file with table column title as pre_modis post_modis pre_vhr post_vhr building_mask road_mask flood_mask,  which list the file paths of corresponding files.

### Steps
1. Create a series masks with the area as 2*2 km^2 to cover one given larger area.
2. Combine the separated litter building and road masks, as well as flood masks as bigger masks (now the size of the masks is only 0.5 km, what we need is 2*2 km^2)
3. Cut VHR, building and road mask, flood mask for one given region
4. Generate MODIS for one given region
5. Generate a .csv file with the matched file path of modis, vhr, and mask
'''

def get_masks_to_cover(given_region, mask_size):
    ''' for a given region, return a serious smaller masks to cover the region.
    Input: given_region (xx), mask_size (km)
    Output: a serious of [left, top, right, bottom]
    '''
    # initialization
    masks_list = []
    reso = 0.0001  # the resolution, about 10 meters
    reso_meter = reso * 100000


    # parameters for masks
    xsize = mask_size * 1000 / reso_meter * reso
    ysize = mask_size * 1000 / reso_meter * reso


    longitudes = np.arange(given_region[0], given_region[2], xsize, dtype = float).tolist()
    latitudes = np.arange(given_region[1], given_region[3], -ysize, dtype = float).tolist()

    for lon in longitudes:
        for lat in latitudes:
            left = lon
            top = lat
            right = left + reso+xsize
            bottom = top - reso+xsize
            masks_list.append([left, top, right, bottom])

    return masks_list


def cut_vhr_given_region(input_ds, mask_geo, save_path):
    ''' cut the one given satellite images (input_ds) within a mask (mask_geo), and save that to save_path
    '''
    left, top, right, bottom = mask_geo

    # input_ds = gdal.Open(one_vhr_path, gdal.GA_ReadOnly)
    projection = input_ds.GetProjection() # 获取投影信息
    # projection = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]' # 投影信息，这里使用WKT格式

    clip_ds = gdal.Translate(save_path, input_ds, 
                             projWin=[left, top, right, bottom], 
                             xRes=0.0001, yRes=0.0001, 
                             outputSRS=projection)

    clip_ds = None  # close


def download_modis_given_region_date(mask_geo, date_range, save_path, filename):
    '''download modis based on given region (mask_geo) and daterange, and save it to save_path
    '''

    left, top, right, bottom = mask_geo
    # geometry, date_range = get_vhr_reg_date(one_vhr_path)
    geometry = ee.Geometry.Polygon([[left, bottom],
                            [left, top],
                            [right, top],
                            [right, bottom]],proj="EPSG:4326") # the proj is determinted in QGIS

    _, one_modis_ima, _ = mod_tol.get_modis_terra_aqua(geometry, ee.DateRange(date_range[0], date_range[1]))      
    
    # for now, the band 7 and the ratio of b1 to b2 are selected
    def b1b2_swir_clip(img):
            return img.select("swir","b1b2_ratio")

    modis_swir_b1b2 = one_modis_ima.map(b1b2_swir_clip)
    geemap.download_ee_image_collection(modis_swir_b1b2, 
                                        out_dir=save_path, 
                                        filenames=[filename],
                                        crs="EPSG:4326")

    one_modis_path = os.path.join(save_path, filename)

    modis_ds = gdal.Open(one_modis_path, gdal.GA_ReadOnly)
    projection = modis_ds.GetProjection() # 获取投影信息

    modis_ds_up = gdal.Translate(one_modis_path, modis_ds, 
                            projWin=[left, top, right, bottom], 
                            xRes=0.0001, yRes=0.0001,
                            outputSRS=projection)

    # print(modis_ds_up.RasterXSize)
    # print(modis_ds_up.RasterYSize)
    # modis_ds_up.GetGeoTransform()
    modis_ds_up = None
    modis_ds = None

def get_vhr_list(spacenet_csv_path, is_train):
    '''extract the VHR image list
    '''
    if is_train:
        spacenet_pd = pd.read_csv(os.path.join(spacenet_csv_path,"sn8_data_train.csv"))
    else:
        spacenet_pd = pd.read_csv(os.path.join(spacenet_csv_path,"sn8_data_val.csv"))
    
    return spacenet_pd['preimg'].tolist(), spacenet_pd['postimg'].tolist()


def get_vhr_reg_date(one_vhr_path):
    '''extract the region and date of the VHR images from SpaceNet8.
    '''
    # Open .tif
    dataset = gdal.Open(one_vhr_path)

    # get the geo range
    geotransform = dataset.GetGeoTransform()
    left = geotransform[0]
    top = geotransform[3]
    right = left + geotransform[1] * dataset.RasterXSize
    bottom = top + geotransform[5] * dataset.RasterYSize

    geometry = ee.Geometry.Polygon([[left, bottom],
                            [left, top],
                            [right, top],
                            [right, bottom]],proj="EPSG:4326") # the proj is determinted in QGIS

    # get the date range
    date_pattern = r"20\d{2}\d{2}\d{2}" # this pattern matches four digits followed by a dash, then two digits followed by a dash, then two digits
    date_match = re.search(date_pattern, one_vhr_path) # this function returns the first match of the pattern in the file path
    if date_match: # if there is a match
        begin_date = date_match.group() # this method returns the matched text
        print(begin_date) # print the date

        begin_date = datetime.datetime.strptime(begin_date, "%Y%m%d") # this function converts the string to a datetime object
        end_date = begin_date + datetime.timedelta(days=1)
    else: # if there is no match
        raise ValueError("No date found in file path")
    
    return geometry, [begin_date, end_date]


def get_one_modis_given_vhr(one_vhr_path):
    '''download modis based on VHR data from Google Earth Engneer
    '''
    geometry, date_range = get_vhr_reg_date(one_vhr_path)

    one_modis_ima = mod_tol.get_modis_terra_aqua(geometry, ee.DateRange(date_range[0], date_range[1]))      

    return one_modis_ima


def get_modis_list_given_vhr(vhr_pathes):
    '''get modis data list based on VHR data
    '''
    modis_list = []
    folder_path = os.path.dirname(vhr_pathes[0])
    upper_path = os.path.dirname(folder_path)
    if "Post" in folder_path:
        save_path = os.path.join(upper_path,"Post_modis")
    elif "pre" in folder_path:
        save_path = os.path.join(upper_path,"Pre_modis")
    else:
        save_path = os.path.join(upper_path,"modis")
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    for one_vhr in vhr_pathes:
        modis_coll = get_one_modis_given_vhr(one_vhr)
        _, filename = os.path.split(one_vhr) # split the file path into path and filename

        geemap.download_ee_image_collection(modis_coll, 
                                            out_dir=save_path, 
                                            filenames=filename)

        modis_list.append(os.path.join(save_path,filename))

    return modis_list

def create_mask():
    '''
    '''


def write_csv(images, masks, idxs, out_csv_filename):
    '''
    '''
    print(f"writing out csv: {out_csv_filename}")
    outfile = open(out_csv_filename, "w")
    header = "preimg,postimg,flood,building,road,roadspeed\n"
    outfile.write(header)
    for i in idxs:
        line = images[0][i]
        for j in range(1, len(images)):
            line += ","+images[j][i]
        for j in range(len(masks)):
            if len(masks[j])!=0:
                line += ","+masks[j][i]
            else:
                line+=","
        line+="\n"
        outfile.write(line)
    outfile.close()


def generate_train_val(root_path, spacenet_csv_path, csv_path):
    ''' generate the train and validation data and .csv

    '''
    # read spacenet_csv_path for VHR data
    pre_vhr_list, post_vhr_list = get_vhr_list(spacenet_csv_path,is_train=True)

    # download modis imagerys and return the modis list
    pre_modis_list, post_modis_list = get_modis(pre_vhr_list,root_path)

 


    

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_path",
                       type=str)
    parser.add_argument("--spacenet_csv_path",
                       type=str)
    parser.add_argument("--csv_path",
                         type=str)
    # parser.add_argument("--val_percent",
    #                     type=float,
    #                     required=False,
    #                     default=0.15)
    args = parser.parse_args()
    return args

if __name__ == "__main__":

    args = parse_args()
    root_path = args.root_path
    spacenet_csv_path = args.spacenet_csv_path
    csv_path = args.csv_path


    ##### train val split as random
    # image_dirs = [os.path.join(root_dir, n) for n in aois]
    # make_train_val_csvs(image_dirs, os.path.join(out_dir, out_csv_basename), val_percent=val_percent)
    # generate_train_val(root_path, spacenet_csv_path, csv_path)
    
    

    one_vhr_path = "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Germany\\Post\\20210718_10500500E6DD3C00.tif"
    # Open .tif
    dataset = gdal.Open(one_vhr_path)

    # get the geo range
    geotransform = dataset.GetGeoTransform()
    left = geotransform[0]
    top = geotransform[3]
    right = left + geotransform[1] * dataset.RasterXSize
    bottom = top + geotransform[5] * dataset.RasterYSize
    get_masks_to_cover(geotransform, 2)
