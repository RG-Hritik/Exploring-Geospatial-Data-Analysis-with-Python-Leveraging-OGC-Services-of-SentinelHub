from sentinelhub import SHConfig

config = SHConfig()

#Set up here sentinelhub account details - client id, secret client id.
if config.instance_id == "":
    print("Warning! To use OGC functionality of Sentinel Hub, please configure the `instance_id`.")

from shapely.geometry import MultiLineString, MultiPolygon, Polygon, box, shape
from sentinelhub import (
    CRS,
    BBox,
    BBoxSplitter,
    CustomGridSplitter,
    DataCollection,
    MimeType,
    MosaickingOrder,
    OsmSplitter,
    SentinelHubDownloadClient,
    SentinelHubRequest,
    TileSplitter,
    UtmGridSplitter,
    UtmZoneSplitter,
    read_data,
) 
#Above imports are for working on different region of interest and some tools to work on.

from sentinelhub import CRS, BBox, DataCollection, MimeType, WcsRequest, WmsRequest
#above imports are for sentinelhub Open Geospatial Consortium (OGC)

# Import necessary libraries
from sentinelhub import WcsRequest, MimeType
import matplotlib.pyplot as plt

# Define bounding box for region of interest and time parameters
betsiboka_bbox = BBox([xmin, ymin, xmax, ymax], crs=CRS.WGS84)
date = ('start_date', 'end_date')

# Define WCS request parameters
wcs_request = WcsRequest(layer='LAYER_NAME',
                         bbox=betsiboka_bbox,
                         time=date,
                         data_collection=DataCollection.SENTINEL2_L1C,
                         resx='10m',
                         resy='10m',
                         image_format=MimeType.TIFF_d32f,
                         custom_url_params={CustomUrlParam.DOWNSAMPLING: 'NEAREST'},
                         instance_id='YOUR_INSTANCE_ID')

data = wcs_request.get_data()
data1 = wcs_request.save_data()

import os
from glob import glob
import pandas as pd
import rioxarray
import gc

# Retrieve all TIFF files from the specified directory
# example
gfiles = glob(os.path.join(path1, '*.tiff'))


#Defining Layerstack funtion for stacking all the downloaded images and converting them to dataframes for further analysis and preprocessing.
def load_sentinel_data(directory_path):      
    file_paths = glob(os.path.join(directory_path, '*.tiff'))
    full_df = pd.DataFrame()
    
    for file_path in file_paths:
        date = file_path.split('\\')[-1].split('_')[7].split('T')[0].replace('-', '_')
        raster_data = rioxarray.open_rasterio(file_path)
        raster_data = raster_data.squeeze().drop("spatial_ref")
        
        raster_data.name = 'd' + date
        df = raster_data.to_dataframe()
        
        if len(df['d' + date][df['d' + date].eq(0.0)]) < 15:
            df.drop("band", axis=1, inplace=True)
            if len(df.index.names) == 1:
                if not (df.index.names[0] == 'y' or df.index.names[0] == 'x'):
                    df = df.set_index(['y', 'x'])
                elif df.index.names[0] == 'y':
                    df = df.set_index(['x'], append=True)
                elif df.index.names[0] == 'x':
                    df = df.reset_index()
                    df = df.set_index(['y', 'x'])
            
            full_df = pd.concat([full_df, df], axis=1)
    
    full_df.index = full_df.index.set_names(['latitude', 'longitude'])
    dataframe = full_df.reset_index()
    gc.collect()
    return dataframe

#using the layerstack function
LayerStack_data = Layerstack_utils.load_sentinel_data(directory_path)

#clipping and selecting relevant data
geometry_points = [Point(xy) for xy in zip(LayerStack_data.longitude, LayerStack_data.latitude)]

gdf = gpd.GeoDataFrame(LayerStack_data, crs="EPSG:4326", geometry=geometry_points)

# Perform spatial join to clip LayerStack data
clipped_data = gpd.sjoin(gdf, geom, how="inner", op='intersects')
clipped_data = clipped_data.drop(columns=['index_right'], errors='ignore')

# Create a copy of the clipped data and drop the 'geometry' column
clipped_data_copy = clipped_data.copy()
clipped_data_copy = clipped_data_copy.drop(columns=['geometry'], axis=1)

# Set latitude and longitude as the index
clipped_data_copy.set_index(['latitude', 'longitude'], inplace=True)

#defining smoothening function to reduce noise in the data
from scipy.signal import savgol_filter as svgl
def savgol(x, window_length=9, polyorder=6): ## smoothening function
    y = svgl(x, window_length, polyorder)
    return pd.Series(y, index=x.index)
## passing parameter to smoothening function
def smooth(x): 
    #print(x)
    return savgol(x, 21, 3)

clipped_data_copy = clipped_data_copy.apply(smooth, axis = 1, result_type='broadcast')



