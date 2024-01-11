import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.features import geometry_window, geometry_mask
from shapely.geometry import box

def calculate_overlap_area(low_res_transform, high_res_transform, high_res_pixel):
    """
    Calculate the overlapping area of a high-resolution pixel on low-resolution pixels.
    """
    # Calculate the boundaries of the high-resolution pixel
    high_res_bounds = rasterio.windows.bounds(Window(col_off=high_res_pixel[1], row_off=high_res_pixel[0], width=1, height=1), high_res_transform)
    
    # Unpack the tuple to get the bounding coordinates
    left, bottom, right, top = high_res_bounds

    # Create a Shapely box geometry from the bounds
    high_res_geom = box(left, bottom, right, top)

    # Calculate the window within the low-resolution raster that overlaps with the high-resolution pixel
    window = geometry_window(low_res_src, [high_res_geom], north_up=True, rotated=False, pad_x=0, pad_y=0)

    # Use the window to read the relevant low-resolution data
    low_res_data = low_res_src.read(1, window=window)

    # Create a mask of the high-res geometry on the low-res data array
    high_res_geom_bounds = high_res_geom.bounds
    transform = low_res_transform * low_res_transform.translation(window.col_off, window.row_off)
    mask = geometry_mask([high_res_geom], transform=transform, invert=True, out_shape=(window.height, window.width))

    # Calculate the area of the high-resolution pixel within each low-resolution pixel
    overlap_areas = mask * (low_res_transform.a * -low_res_transform.e)  # Pixel size of low-res raster

    return low_res_data, overlap_areas

# Set the file paths
low_res_path = "E:/code/Py_workplace/satellite_flooding/Data/US socio-economic/GHSL_CA.tif"
high_res_path = "E:/code/Py_workplace/satellite_flooding/Data/GFD/US_census_track/DFO4444_cut_perm_water.tif"
output_path = "E:/code/Py_workplace/satellite_flooding/Data/Processed/high_res_weighted_population.tif"

# Open the low and high resolution rasters
with rasterio.open(low_res_path) as low_res_src, rasterio.open(high_res_path) as high_res_src:

    # Initialize an array to hold the high resolution population data
    high_res_population = np.zeros((high_res_src.height, high_res_src.width), dtype=np.float32)

    # Loop over each pixel in the high-resolution raster
    for row in range(high_res_src.height):
        for col in range(high_res_src.width):
            # Calculate the low-res data and overlap areas
            low_res_data, overlap_areas = calculate_overlap_area(low_res_src.transform, high_res_src.transform, (row, col))

            # Treat negative population values as zero
            low_res_data = np.maximum(low_res_data, 0)

            # Calculate the weighted population for the high-res pixel
            weighted_population = np.sum(low_res_data * overlap_areas) / np.sum(overlap_areas)
            high_res_population[row, col] = weighted_population

    # Update metadata for writing the output raster
    high_res_meta = high_res_src.meta.copy()
    high_res_meta.update(dtype='float32', count=1, compress='lzw')

    # Write the resampled population data to the output raster
    with rasterio.open(output_path, 'w', **high_res_meta) as out_raster:
        out_raster.write(high_res_population, 1)

print(f"Area-weighted resampling completed. Output saved to {output_path}")
