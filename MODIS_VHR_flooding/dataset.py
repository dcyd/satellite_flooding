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
# os.environ['HTTP_PROXY'] = r'http://127.0.0.1:7890'
# os.environ['HTTPS_PROXY'] = r'https://127.0.0.1:7890'
# os.environ['PROJ_LIB'] = r'./osgeo/data/proj'



'''
Final dataset:
    For one sample, there are three types of images, including MODIS, VHR from SpaceNet8, and flooding masks.
    MODIS: pre and post flooding.
    VHR: pre and post flooding.
    mask: two mask, one for (flooded building and non-flooded building), another for (flooded and unflooded roads)

    The region and data of the samples are based on SpaceNet8.
'''

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


def get_modis_list_given_vhr(vhr_pathes, root_path):
    '''get modis data list based on VHR data
    '''
    pre_modis_list = []

    for one_vhr in vhr_pathes:
        modis_coll = get_one_modis_given_vhr(one_vhr)

        geemap.download_ee_image_collection(modis_coll)

    return pre_modis_list, post_modis_list

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
    generate_train_val(root_path, spacenet_csv_path, csv_path)

