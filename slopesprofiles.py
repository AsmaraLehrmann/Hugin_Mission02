import os
import numpy as np
import pandas as pd
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsRaster

# Set input parameters—update these paths as needed.
shapefile_folder = '/Users/alehrmann/Documents/Research_files/West_Antarctica/QGIS/HuginMission2/rib_profiles'
geotiff_file = '/Users/alehrmann/Documents/Research_files/West_Antarctica/QGIS/HuginMission2/slope_rasterterrainanalysis.tif'
output_excel = '/Users/alehrmann/Documents/Research_files/West_Antarctica/Amundsen_Sea/Dotson/Ribs/profiles/Drumlin3_profileslopes_combined_output.xlsx'

# Before writing, ensure the output directory exists.
output_folder = os.path.dirname(output_excel)
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    print(f"Created output folder: {output_folder}")

# Load the slope raster.
slope_raster = QgsRasterLayer(geotiff_file, "slope_raster")
if not slope_raster.isValid():
    print("Raster layer failed to load! Check the GeoTIFF path and CRS.")
else:
    print("Raster layer loaded successfully.")

# Dictionary to hold results for each shapefile (key: sheet name, value: DataFrame)
results = {}

# Process each shapefile in the specified folder.
for file_name in os.listdir(shapefile_folder):
    if file_name.lower().endswith(".shp"):
        shp_path = os.path.join(shapefile_folder, file_name)
        vector_layer = QgsVectorLayer(shp_path, file_name, "ogr")
        
        if not vector_layer.isValid():
            print(f"Failed to load shapefile: {file_name}")
            continue
        
        print(f"Processing {file_name}...")
        
        # Extract the field names from the vector layer.
        field_names = [field.name() for field in vector_layer.fields()]
        # The header will include existing attribute fields,
        # plus the X and Y coordinate, and the slope value.
        header = field_names + ["X coordinate", "Y coordinate", "slope_value"]
        rows = []
        coords = []  # This list will store (x, y) tuples for each feature.
        
        # Process each feature (point) in the shapefile.
        for feature in vector_layer.getFeatures():
            geom = feature.geometry()
            if geom.isEmpty():
                x_coord = None
                y_coord = None
                slope_val = None
            else:
                # Assumes the geometry is a point.
                point = geom.asPoint()
                x_coord = point.x()
                y_coord = point.y()
                # Identify the raster value at the point location.
                result = slope_raster.dataProvider().identify(point, QgsRaster.IdentifyFormatValue)
                if result.isValid():
                    # For a single-band raster, the band key is usually 1.
                    slope_val = result.results().get(1, None)
                else:
                    slope_val = None
            
            # Build the row: existing attribute values + X coordinate + Y coordinate + slope value.
            row = [feature[field] for field in field_names] + [x_coord, y_coord, slope_val]
            rows.append(row)
            coords.append((x_coord, y_coord))
        
        # Compute cumulative distances along the profile.
        # For the first point, distance is zero. For each subsequent point,
        # add the Euclidean distance from the previous point.
        distances = []
        cumulative = 0.0
        prev_point = None
        for point in coords:
            if prev_point is None:
                d = 0.0
            else:
                # If either coordinate is missing, assume zero distance increment.
                if None in (prev_point[0], prev_point[1], point[0], point[1]):
                    d = 0.0
                else:
                    d = np.sqrt((point[0] - prev_point[0])**2 + (point[1] - prev_point[1])**2)
            cumulative += d
            distances.append(cumulative)
            prev_point = point
        
        # Create a DataFrame for this shapefile.
        df = pd.DataFrame(rows, columns=header)
        # Insert the distances as a new column.
        df["distance"] = distances
        
        # Use the shapefile's base name (without extension) as the sheet name.
        sheet_name = os.path.splitext(file_name)[0]
        results[sheet_name] = df
        print(f"Processed {len(rows)} features from {file_name}.")
        print(f"Added distance column with cumulative distances (first value: {distances[0]}, last value: {distances[-1]}).")

# Write all the DataFrames to a single Excel file with one sheet per shapefile.
with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
    for sheet_name, df in results.items():
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"Sheet '{sheet_name}' written to Excel file.")

print(f"\nAll done! The output Excel file with multiple sheets has been saved to '{output_excel}'.")
