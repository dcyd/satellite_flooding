import csv
import copy
import os
from osgeo import gdal
import datetime

import re

from dataset import download_modis_given_region_date


def write_csv(images, out_csv_filename):
    print(f"writing out csv: {out_csv_filename}")
    outfile = open(out_csv_filename, "w")
    header = "preimg,postimg,building,road,roadspeed,flood,flood_road,flood_building,pre_modis,post_modis\n"
    outfile.write(header)
    for i in range(len(images[0])):
        line = images[0][i]
        for j in range(1, len(images)):
            line += ","+images[j][i]
        line+="\n"
        outfile.write(line)
    outfile.close()


# sn8_train_path = "E:\\code\\Py_workplace\\spacenet8\\Data\\train_val_csv\\sn8_data_train.csv"
sn8_val_path = "E:\\code\\Py_workplace\\spacenet8\\Data\\train_val_csv\\sn8_data_val.csv"



# csc_path = sn8_train_path
csc_path = sn8_val_path
# read the sn8_data_train.csv and sn8_data_val.csv
all_data_types = ["preimg", "postimg", "building", "road", "roadspeed", "flood", "flood_road", "flood_building", "pre_modis", "post_modis"]
        
data_to_load = all_data_types[0:6]

files = []

dict_template = {}
for i in all_data_types:
    dict_template[i] = None

with open(csc_path, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        in_data = copy.copy(dict_template)
        for j in data_to_load:
            in_data[j]=row[j]
        files.append(in_data)

print("loaded", len(files), "image filepaths")



file_date_table = {'104001003E791C00':'20180701',
                  '10500500C4DD7000':'20210211',
                  '10500500C4DD7100':'20210211',
                  '10200100B49A4000':'20210711',
                  '10200100B396B200':'20210711',
                  '10500500E6DD3C00':'20210718',
                  '1040050035DC3B00':'20210721',
                  '10300100C4AB0300':'20210831',
                  '10300100C46F5900':'20210831',
                  '10300100C51FE500':'20210831',
                  '10300100C459C000':'20210831',
                  '10300100C4171800':'20210831',
                  '10300100C5474600':'20210831',
                  '10300100C5735600':'20210831',
                  '1050010026B2FC00':'20210831',
                  '1050010026B2FD00':'20210831',
                  '10300100C52CAD00':'20210905',
                  '10300100C57EC700':'20210911',
                  '10300100C540A500':'20210911',
                  '1050010019602400':'20191023',
                  '105001001A0FFC00':'20191128',
                  '10400100568CE100':'20200109',
                  '105001001B76D700':'20200221',
                  '105001001DD56B00':'20200617',
                  '105001001E0A3300':'20200620',
                  '10300100B07DF800':'20201029',
                  '10300100AF395C00':'20201122',
                  '10300100B058C700':'20201122',
                  '104001006504F400':'20210103',
                  '1050010021BB3200':'20210105',
                  '10300100B5827200':'20210107',
                  '10300100B3863900':'20210113',
                  '10300100B4D31D00':'20210129',
                  '10300100B3414E00':'20210129',
                  '10400100684A4B00':'20210421',
                  '10500100244DA100':'20210514',
                  '10300100C3374500':'20210727',
                  }


preimg = []
postimg = []
building = []
road = []
roadspeed = []
flood =[]
flood_road = []
flood_building = []
pre_modis = []
post_modis = []

for path_i  in files:
    pre_modis_root_path = os.path.join(os.path.dirname(os.path.dirname(path_i['preimg'])), "pre_modis")
    post_modis_root_path = os.path.join(os.path.dirname(os.path.dirname(path_i['preimg'])), "post_modis")

    if not os.path.exists(pre_modis_root_path):
        os.makedirs(pre_modis_root_path)
    if not os.path.exists(post_modis_root_path):
        os.makedirs(post_modis_root_path)


    preimg_path = path_i['preimg']
    postimg_path = path_i['postimg']
    
    pre_modis_name = f"premodis_{os.path.basename(preimg_path).split('.')[0]}.tif"
    pre_modis_path = os.path.join(pre_modis_root_path, pre_modis_name)

    post_modis_name = f"postmodis_{os.path.basename(preimg_path).split('.')[0]}.tif"
    post_modis_path = os.path.join(post_modis_root_path, post_modis_name)

    # read pre vhr to determine the region
    dataset = gdal.Open(preimg_path)

    # get the geo range
    geotransform = dataset.GetGeoTransform()
    left = geotransform[0]
    top = geotransform[3]
    right = left + geotransform[1] * dataset.RasterXSize
    bottom = top + geotransform[5] * dataset.RasterYSize
    reso = [geotransform[1],geotransform[5]]


    # based on the file name to determine the post and pre daterange
    date_pattern = r"20\d{2}\d{2}\d{2}"

    date_match = re.search(date_pattern, file_date_table[os.path.basename(preimg_path).split('_')[0]])
    if date_match: # if there is a match
        begin_date = date_match.group() # this method returns the matched text
        begin_date = datetime.datetime.strptime(begin_date, "%Y%m%d")
        end_date = begin_date + datetime.timedelta(days=1)
    else:
        raise ValueError("No date found in file path")
    pre_daterange = [begin_date, end_date]

    date_match = re.search(date_pattern, file_date_table[os.path.basename(postimg_path).split('_')[0]])
    if date_match: # if there is a match
        begin_date = date_match.group() # this method returns the matched text
        begin_date = datetime.datetime.strptime(begin_date, "%Y%m%d")
        end_date = begin_date + datetime.timedelta(days=1)
    else:
        raise ValueError("No date found in file path")
    post_daterange = [begin_date, end_date]

    # with the region and daterange, download modis
    if not os.path.exists(os.path.join(pre_modis_root_path,pre_modis_name)):
        download_modis_given_region_date([left,top,right,bottom], pre_daterange, pre_modis_root_path, pre_modis_name,reso)

    if not os.path.exists(os.path.join(post_modis_root_path,post_modis_name)):
        download_modis_given_region_date([left,top,right,bottom], post_daterange, post_modis_root_path, post_modis_name,reso)

    preimg.append(path_i['preimg'])
    postimg.append(path_i['postimg'])
    building.append(path_i['building'])
    road.append(path_i['road'])
    roadspeed.append(path_i['roadspeed'])
    flood.append(path_i['flood'])

    mask_path = os.path.dirname(path_i['road'])

    out_road_imagename = f"flood_road_{os.path.basename(preimg_path).split('.')[0]}.tif"
    out_building_imagename = f"flood_building_{os.path.basename(preimg_path).split('.')[0]}.tif"
    flood_road.append(os.path.join(mask_path, out_road_imagename))
    flood_building.append(os.path.join(mask_path, out_building_imagename))

    pre_modis.append(pre_modis_path)
    post_modis.append(post_modis_path)


# save the .csv containing the information of data for training

all_images = [preimg,postimg,building,road,roadspeed,flood,flood_road,flood_building,pre_modis,post_modis]

# write_csv(all_images, os.path.join(os.path.dirname(sn8_train_path), "modis_train.csv"))
write_csv(all_images, os.path.join(os.path.dirname(sn8_val_path), "modis_val.csv"))






