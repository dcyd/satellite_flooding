# Chongyang Du
# Jan 2, 2024

# use this template to run the flood stats functions (area, population, etc.)
# on an image collection and export results as a .tif

import ee
import geemap
ee.Initialize()

# from flood_stats import pop_utils
import time, csv

def get_flood_pop_pixel(flood_img):
    """
    Args:
        floodImage : the standard Earth Engine Image object outputted by the map_DFO_event function
        roiGEO : the region of interest as an Earth Engine Geometry object

    Returns:
    -an image of people in the mapped flood from WorldPop data

    """
    import ee
    import geemap
    ee.Initialize()
    # ee.Authenticate()
    roi_geo = flood_img.geometry()

    # Import the LandScan image collection & permannt water mask
    perm_water = ee.Image("JRC/GSW1_0/GlobalSurfaceWater").select("transition").eq(1).unmask()
    # print('Band names:', flood_img.bandNames().getInfo())
    def maskImages(img):
        non_flood = img.select("flooded")
        water_mask = non_flood.multiply(perm_water.neq(1))
        return img.select("flooded").mask(water_mask)

    def durationImages(img):
            non_flood = img.select("flooded")
            water_mask = non_flood.multiply(perm_water.neq(1))
            return img.select("duration").mask(water_mask)

    # Extract the final flood extent image data as its own variable for analysis
    # flood_extent = maskImages(ee.Image(flood_img.select("flooded")))
    # flood_duration = durationImages(ee.Image(flood_img.select("flood_duration")))
    flood_extent = maskImages(ee.Image(flood_img))
    flood_duration = durationImages(ee.Image(flood_img))


    # # get pop from projects/global-flood-db/landscan
    # # Get event year, match with the population year and clip to study are
    # pop_all = ee.ImageCollection("projects/global-flood-db/landscan")
    # event_year = ee.Date(flood_img.get('began')).get('year')
    # pop_img = ee.Image(pop_all.filterMetadata('year', 'equals', event_year)\
    #                 .first()).clip(roi_geo)
    # pop_img = pop_img.updateMask(pop_img.gte(0)) # mask out bad data with negative values

    # get pop from JRC/GHSL/P2016/POP_GPW_GLOBE_V1
    pop_all = ee.ImageCollection("JRC/GHSL/P2016/POP_GPW_GLOBE_V1")
    # Get event year to match with the population year
    # pop_img = ee.Image(pop_all.filterMetadata('system:index', 'equals', '2000')\
    #                 .first()).clip(roi_geo)
    pop_img = ee.Image(pop_all.filterMetadata('system:index', 'equals', '2015')\
                    .first()).clip(roi_geo)


    # Mask the world population dataset using the flood extent layer
    pop_masked = pop_img.updateMask(flood_extent)

    return flood_extent, flood_duration, pop_img, pop_masked


# Image Collection of flood maps, each needs layer called "flooded" that
# is 1 = flooded, 0 = not flooded
gfd = ee.ImageCollection('projects/global-flood-db/gfd_v3').filterMetadata('id','greater_than',4335)

# Create Error Log file
log_file = "error_logs/event_stats/pop_error_log_{0}.csv".format(time.strftime("%d_%m_%Y"))
with open(log_file,"w", newline='') as out_file:
    wr = csv.writer(out_file)
    wr.writerow(["error_type", "dfo_id", "error_message"])

# Create list of events from input fusion table
event_ids = ee.List(gfd.aggregate_array('id')).sort()
id_list = event_ids.getInfo()
id_list = [int(i) for i in id_list]

# for event_id in id_list:
# event_id = id_list[0]
event_id = 4444
# Get event date range, they can be passed as Strings
flood_event = ee.Image(gfd.filterMetadata('id', 'equals', event_id).first())

# try:
# Calculate flood stats
# flood_stats = pop_utils.getFloodPopbyCountry_GHSLTimeSeries(flood_event)
flood_extent, flood_duration, pop_img, pop_masked = get_flood_pop_pixel(flood_event)
# index = flood_stats.get("id").getInfo()
print("calculated results, exporting results for DFO {0}...".format(event_id))

# 定义感兴趣的区域
region = pop_img.geometry()

# 设置下载参数
output_dir = '/download/'
scale = pop_img.projection().nominalScale()  # 设置所需的空间分辨率
file_format = 'GeoTIFF'  # 设置所需的文件格式

# 下载图像集合

filename = "flooded_{0}.tif".format(event_id)
geemap.download_ee_image(flood_extent, scale=scale, region=region, filename=filename, crs="EPSG:4326")

filename = "flood_duration_{0}.tif".format(event_id)
geemap.download_ee_image(flood_duration, scale=scale, region=region, filename=filename, crs="EPSG:4326")

filename = "pop_{0}.tif".format(event_id)
geemap.download_ee_image(pop_img, scale=scale, region=region, filename=filename, crs="EPSG:4326")

filename = "pop_flooded_{0}.tif".format(event_id)
geemap.download_ee_image(pop_masked, scale=scale, region=region, filename="pop_masked_4444.tif", crs="EPSG:4326")


print('Done!')