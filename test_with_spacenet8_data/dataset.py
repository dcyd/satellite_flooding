import time
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

def get_masks_to_cover(given_region, mask_size = 2):
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
            right = left + xsize
            bottom = top - ysize
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


def download_modis_given_region_date(mask_geo, date_range, save_path, filename,res=[0.0001,-0.0001]):
    '''download modis based on given region (mask_geo) and daterange, and save it to save_path
    '''

    left, top, right, bottom = mask_geo
    # geometry, date_range = get_vhr_reg_date(one_vhr_path)
    geometry = ee.Geometry.Polygon([[left-0.1, top+0.1],
                            [right+0.1, top+0.1],
                            [right+0.1, bottom-0.1],
                            [left-0.1, bottom-0.1]],proj="EPSG:4326") # the proj is determinted in QGIS

    # geometry = ee.Geometry.Polygon([[right, bottom],
    #                         [right, top],
    #                         [left, top],           
    #                         [left, bottom]],proj="EPSG:4326") # the proj is determinted in QGIS

    _, one_modis_ima, _ = mod_tol.get_modis_terra_aqua(geometry, ee.DateRange(date_range[0], date_range[1]))      
    
    # for now, the band 7 and the ratio of b1 to b2 are selected
    def b1b2_swir_clip(img):
            return img.select("swir","b1b2_ratio")

    modis_swir_b1b2 = one_modis_ima.map(b1b2_swir_clip)
    try:
        geemap.download_ee_image_collection(modis_swir_b1b2, 
                                            out_dir=save_path, 
                                            region=geometry,
                                            filenames=['buffer.tif'],
                                            crs="EPSG:4326")

    except BaseException as e:
        print(e)
        print("waiting and try again")
        time.sleep(2)
        geemap.download_ee_image_collection(modis_swir_b1b2, 
                                            out_dir=save_path, 
                                            region=geometry,
                                            filenames=['buffer.tif'],
                                            crs="EPSG:4326")

    one_modis_path = os.path.join(save_path, 'buffer.tif')

    modis_ds = gdal.Open(one_modis_path, gdal.GA_ReadOnly)
    projection = modis_ds.GetProjection() # 获取投影信息

    # modis_ds_up = gdal.Translate(os.path.join(save_path, filename), modis_ds, 
    #                     projWin=[left, top, right, bottom], 
    #                     xRes=res[0], yRes=res[1],
    #                     width = 1300, height = 1300,
    #                     outputSRS=projection)
    

    # if modis_ds_up is None:
    #     print("turn over top and bottom, and try to download again")
    #     modis_ds_up = gdal.Translate(os.path.join(save_path, filename), modis_ds, 
    #                 projWin=[left, bottom, right, top], 
    #                 xRes=res[0], yRes=res[1],
    #                 width = 1300, height = 1300,
    #                 outputSRS=projection)

    ds = gdal.Warp(os.path.join(save_path, filename), one_modis_path,
                    dstSRS=projection,
                    outputBounds = [left, bottom, right, top],
                    format='GTiff', 
                    xRes=res[0], yRes=res[1],
                    resampleAlg=gdal.GRIORA_NearestNeighbour,
                    workingType = gdal.GDT_Float32,
                    outputType=gdal.GDT_Float32)
    modis_ds
    if ds is None:
        return False
    else:
        ds = None
        return True
        
# try:
#     可能出错的地方
# except BaseException as e：
#     print(e)
# else:
#     没有错误时要执行代码
# finally：
#     不管有没有错误都要执行的代码

# print(modis_ds_up.RasterXSize)
# print(modis_ds_up.RasterYSize)
# modis_ds_up.GetGeoTransform()
    

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


def identify_overlap(tif_path_1, tif_path_2):
    '''identify the overlap region for two given .tif file
    output: [left top right bottom]
    '''
    # tif_path_1 = "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Germany\\Pre\\20180701_104001003E791C00.tif"
    # tif_path_2 = "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Germany\\Post\\20210718_10500500E6DD3C00.tif"

    # Open .tif
    tif_1 = gdal.Open(tif_path_1)
    geotransform_1 = tif_1.GetGeoTransform()
    left_1 = geotransform_1[0]
    top_1 = geotransform_1[3]
    right_1 = left_1 + geotransform_1[1] * tif_1.RasterXSize
    bottom_1 = top_1 + geotransform_1[5] * tif_1.RasterYSize

    tif_2 = gdal.Open(tif_path_2)
    geotransform_2 = tif_2.GetGeoTransform()
    left_2 = geotransform_2[0]
    top_2 = geotransform_2[3]
    right_2 = left_2 + geotransform_2[1] * tif_2.RasterXSize
    bottom_2 = top_2 + geotransform_2[5] * tif_2.RasterYSize

    left = max(left_1,left_2)
    top = min(top_1,top_2)

    right = min(right_1,right_2)
    bottom = max(bottom_1,bottom_2)

    # print([left_1, top_1, right_1, bottom_1])
    # print([left_2, top_2, right_2, bottom_2])
    # print([left, top, right, bottom])
    # print()

    if (left<right) and (top>bottom):
        return [left, top, right, bottom]
    else:
        return []

def write_csv(images, out_csv_filename):
    print(f"writing out csv: {out_csv_filename}")
    outfile = open(out_csv_filename, "w")
    header = "pre_vhr,post_vhr,pre_modis,post_modis\n"
    outfile.write(header)
    for i in range(len(images[0])):
        line = images[0][i]
        for j in range(1, len(images)):
            line += ","+images[j][i]
        line+="\n"
        outfile.write(line)
    outfile.close()


if __name__ == "__main__":
    # for germany
    # pre_vhrs = ["E:\\code\\Py_workplace\\satellite_flooding\\Data\\Germany\\Pre\\20180701_104001003E791C00.tif",
    #             "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Germany\\Pre\\20210211_10500500C4DD7000.tif",
    #             "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Germany\\Pre\\20210211_10500500C4DD7100.tif",
    #             "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Germany\\Pre\\20210711_10200100B49A4000.tif",
    #             "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Germany\\Pre\\20210711_10200100B396B200.tif",]
    # post_vhrs = ["E:\\code\\Py_workplace\\satellite_flooding\\Data\\Germany\\Post\\20210718_10500500E6DD3C00.tif",
    #              "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Germany\\Post\\20210721_1040050035DC3B00.tif"]
    
    # root_path = "E:\\code\\Py_workplace\\satellite_flooding\\train_val_data\\Germany"

    # for Louisiana
    pre_vhrs = ["E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20210103_104001006504F400.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20191023_1050010019602400.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20201029_10300100B07DF800.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20200620_105001001E0A3300.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20210421_10400100684A4B00.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20210514_10500100244DA100.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20201122_10300100AF395C00.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20200221_105001001B76D700.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20201122_10300100B058C700.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20210727_10300100C3374500.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20200617_105001001DD56B00.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20200109_10400100568CE100.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20210129_10300100B4D31D00.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20210113_10300100B3863900.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20210129_10300100B3414E00.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20210105_1050010021BB3200.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20191128_105001001A0FFC00.tif",
                "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Pre\\20210107_10300100B5827200.tif",]
    

    post_vhrs = ["E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Post\\20210911_10300100C540A500.tif",
                 "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Post\\20210911_10300100C57EC700.tif",
                 "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Post\\20210831_10300100C46F5900.tif",
                 "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Post\\20210831_10300100C4171800.tif",
                 "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Post\\20210831_10300100C5474600.tif",
                 "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Post\\20210905_10300100C52CAD00.tif",
                 "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Post\\20210831_10300100C459C000.tif",
                 "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Post\\20210831_10300100C5735600.tif",
                 "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Post\\20210831_1050010026B2FD00.tif",
                 "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Post\\20210831_10300100C4AB0300.tif",
                 "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Post\\20210831_1050010026B2FC00.tif",
                 "E:\\code\\Py_workplace\\satellite_flooding\\Data\\Louisiana\\Post\\20210831_10300100C51FE500.tif",]
    
    root_path = "E:\\code\\Py_workplace\\satellite_flooding\\train_val_data\\Louisiana"


    pre_vhr_lists = []
    post_vhr_lists = []
    pre_modis_lists = []
    post_modis_lists = []

    # Cut vhr and download modis, and save the path to .csv
    for post_vhr in post_vhrs:
        print(post_vhr)
        for pre_vhr in pre_vhrs:
            print(pre_vhr)
            overlap_region = identify_overlap(pre_vhr, post_vhr)
            if len(overlap_region)!=0:
                mask_list = get_masks_to_cover(overlap_region, mask_size = 2)
                _, pre_file_name = os.path.split(pre_vhr)
                pre_file_name, _ = os.path.splitext(pre_file_name)
                post_vhr_root_path = os.path.join(root_path, "post_vhr")
                pre_vhr_root_path = os.path.join(root_path, "pre_vhr")
                post_modis_root_path = os.path.join(root_path, "post_modis")
                pre_modis_root_path = os.path.join(root_path, "pre_modis")

                pre_vhr_ds = gdal.Open(pre_vhr, gdal.GA_ReadOnly)
                post_vhr_ds = gdal.Open(post_vhr, gdal.GA_ReadOnly)

                _, pre_daterange = get_vhr_reg_date(pre_vhr)
                _, post_daterange = get_vhr_reg_date(post_vhr)

                tag = 0
                print("cutting vhr and downloading modis")
                for one_mask in mask_list:
                    file_name = pre_file_name+"_"+str(tag)+".tif"
                    tag = tag+1
                    # cut vhr
                    if not os.path.exists(os.path.join(pre_vhr_root_path,file_name)):
                        cut_vhr_given_region(pre_vhr_ds, one_mask, os.path.join(pre_vhr_root_path,file_name))

                    if not os.path.exists(os.path.join(post_vhr_root_path,file_name)):
                        cut_vhr_given_region(post_vhr_ds, one_mask, os.path.join(post_vhr_root_path,file_name))

                    # download modis

                    if not os.path.exists(os.path.join(pre_modis_root_path,file_name)):
                        download_modis_given_region_date(one_mask, pre_daterange, pre_modis_root_path, file_name)
                    if not os.path.exists(os.path.join(post_modis_root_path,file_name)):
                        download_modis_given_region_date(one_mask, post_daterange, post_modis_root_path, file_name)

                    pre_vhr_lists.append(os.path.join(pre_vhr_root_path,file_name))
                    post_vhr_lists.append(os.path.join(post_vhr_root_path,file_name))
                    pre_modis_lists.append(os.path.join(pre_modis_root_path,file_name))
                    post_modis_lists.append(os.path.join(post_modis_root_path,file_name))

                pre_vhr_ds = None
                post_vhr_ds = None

    # all_images = [[],[]]
    all_images = [pre_vhr_lists,post_vhr_lists,pre_modis_lists,post_modis_lists]
    write_csv(all_images, os.path.join(root_path, "germany.csv"))
