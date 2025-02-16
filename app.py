import matplotlib
matplotlib.use('Agg')  # Prevent Matplotlib GUI errors

from flask import Flask, render_template, request, jsonify
import requests
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from shapely.geometry import Point
from geopy.distance import geodesic
import datetime
import os
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter

app = Flask(__name__)

# Ensure static directory exists for storing images
os.makedirs("static", exist_ok=True)

# Function to fetch earthquake data from USGS API
def fetch_earthquake_data(start_date, end_date, min_magnitude, max_magnitude, min_lat, max_lat, min_lon, max_lon):
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": start_date,
        "endtime": end_date,
        "minmagnitude": min_magnitude,
        "maxmagnitude": max_magnitude,
        "minlatitude": min_lat,
        "maxlatitude": max_lat,
        "minlongitude": min_lon,
        "maxlongitude": max_lon
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Route for homepage
@app.route("/")
def home():
    return render_template("index.html")

# Route to fetch earthquake data & generate map
@app.route("/get_earthquake_data", methods=["POST"])
def get_earthquake_data():
    data = request.json  

    try:
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        min_magnitude = float(data.get("min_magnitude", 0))
        max_magnitude = float(data.get("max_magnitude", 10))
        min_lat = float(data.get("min_lat", -90))
        max_lat = float(data.get("max_lat", 90))
        min_lon = float(data.get("min_lon", -180))
        max_lon = float(data.get("max_lon", 180))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid input values"}), 400

    # Fetch earthquake data
    result = fetch_earthquake_data(start_date, end_date, min_magnitude, max_magnitude, min_lat, max_lat, min_lon, max_lon)

    if "error" in result:
        return jsonify({"error": result["error"]}), 500

    earthquakes = result.get("features", [])
    if not earthquakes:
        return jsonify({"message": "No earthquake data found!"})

    earthquake_list = []
    for quake in earthquakes:
        properties = quake["properties"]
        geometry = quake["geometry"]
        if properties and geometry:
            earthquake_list.append({
                "Time": pd.to_datetime(properties["time"], unit="ms").strftime('%Y-%m-%d %H:%M:%S'),
                "Place": properties["place"],
                "Magnitude": properties["mag"],
                "Depth": round(geometry["coordinates"][2], 2),
                "Latitude": round(geometry["coordinates"][1], 4),
                "Longitude": round(geometry["coordinates"][0], 4)
            })

    df = pd.DataFrame(earthquake_list)

    if df.empty:
        return jsonify({"message": "No earthquake data available!"})

    # Convert Time column to datetime and extract Date
    df["Time"] = pd.to_datetime(df["Time"])
    df["Date"] = df["Time"].dt.date

    # Group by date to calculate daily earthquake counts
    earthquake_stats = df.groupby("Date").size().reset_index(name="Count")
    earthquake_stats.loc[len(earthquake_stats)] = ["Total", earthquake_stats["Count"].sum()]

    # Convert DataFrame to GeoDataFrame
    geometry = [Point(xy) for xy in zip(df["Longitude"], df["Latitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # GERD location
    gerd_lat, gerd_lon = 11.214, 35.093  

    def calculate_distance(lat1, lon1, lat2, lon2):
        return geodesic((lat1, lon1), (lat2, lon2)).km

    # Generate and save map
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"earthquake_map_{now}.png"
    filepath = f"static/{filename}"

    plt.figure(figsize=(10, 20))  
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([33, 42, 3, 15], crs=ccrs.PlateCarree())

    # Add map features
    ax.add_feature(cfeature.COASTLINE, alpha=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle='--', alpha=0.5)
    ax.add_feature(cfeature.LAKES, color='blue', alpha=0.5)
    ax.add_feature(cfeature.RIVERS, color='blue', alpha=0.5)

    # Add grid lines
    ax.gridlines(draw_labels=False, linestyle='--', alpha=0.7)

    # Manually set tick labels for consistent display on all sides
    xticks = range(33, 43, 2)  # Longitude ticks
    yticks = range(3, 16, 2)  # Latitude ticks

    ax.set_xticks(xticks, crs=ccrs.PlateCarree())
    ax.set_yticks(yticks, crs=ccrs.PlateCarree())
    ax.xaxis.set_major_formatter(LongitudeFormatter())
    ax.yaxis.set_major_formatter(LatitudeFormatter())
    ax.tick_params(axis="both", which="major", labelsize=14)

    # Display tick labels on all sides
    ax.tick_params(top=True, bottom=True, left=True, right=True, labeltop=True, labelbottom=True, labelleft=True, labelright=True)

    # Plot earthquake points
    for _, row in gdf.iterrows():
        color = "pink" if row["Magnitude"] <= 4.4 else "hotpink" if row["Magnitude"] <= 4.6 else "magenta" if row["Magnitude"] <= 5.0 else "red"
        size = 30 if row["Magnitude"] <= 4.4 else 60 if row["Magnitude"] <= 4.6 else 90 if row["Magnitude"] <= 5.0 else 120

        # Draw dashed lines and distance labels for earthquakes >5.0
        if row["Magnitude"] > 5.0:
            distance = calculate_distance(gerd_lat, gerd_lon, row.geometry.y, row.geometry.x)
            ax.plot([gerd_lon, row.geometry.x], [gerd_lat, row.geometry.y], color='black', linestyle='dashed', linewidth=1, transform=ccrs.PlateCarree())
            ax.text((gerd_lon + row.geometry.x) / 2, (gerd_lat + row.geometry.y+0.2) / 2, f"{distance:.1f} km", color='black', fontsize=12, transform=ccrs.PlateCarree(), ha='right',rotation=-20)

        ax.scatter(row.geometry.x, row.geometry.y, facecolor="none", edgecolor=color, s=size, transform=ccrs.PlateCarree())

    # Add GERD location
    ax.scatter(gerd_lon, gerd_lat, color='black', s=100, marker='^', transform=ccrs.PlateCarree(), label="GERD Location")

    # Add lake and river names
    ax.text(37.5, 6.7, "Lake Turkana", color="blue", fontsize=10, transform=ccrs.PlateCarree())
    ax.text(37, 12.5, "Lake Tana", color="blue", fontsize=10, transform=ccrs.PlateCarree())
    ax.text(40.5, 10.5, "Awash River", color="blue", fontsize=10, transform=ccrs.PlateCarree(),rotation=45)
    ax.text(35.5, 10.5, "Blue Nile", color="blue", fontsize=10, transform=ccrs.PlateCarree())
    ax.text(34.5, 5.5, "Baro River", color="blue", fontsize=10, transform=ccrs.PlateCarree())
    # Add legend
    legend_elements = [
        plt.scatter([], [], facecolor="none", edgecolor="pink", s=30, label="<=4.40"),
        plt.scatter([], [], facecolor="none", edgecolor="hotpink", s=60, label="4.41-4.6"),
        plt.scatter([], [], facecolor="none", edgecolor="magenta", s=90, label="4.61-5.0"),
        plt.scatter([], [], facecolor="none", edgecolor="red", s=120, label=">5.00"),
        plt.scatter([], [], color='black', s=100, marker='^', label="GERD Location"),
    ]
    ax.legend(handles=legend_elements, loc="lower left", fontsize=10, title="Legend")

    # Add the table inside the plot (adjust bbox for correct positioning)
    table_data = earthquake_stats.values.tolist()
    table_columns = ["Date", "Frequency"]

    table = ax.table(
        cellText=table_data,
        colLabels=table_columns,
        cellLoc='center',
        colLoc='center',
        bbox=[0.65, 0.02, 0.3, 0.15],  # Position inside the plot
        zorder=10
    )

    # Customize the table appearance
    table.auto_set_font_size(False)
    table.set_fontsize(10)

    # Save figure
    plt.savefig(filepath, dpi=900, bbox_inches="tight")
    plt.close()

    return jsonify({"image_url": filepath, "table_data": earthquake_list})

if __name__ == "__main__":
    app.run(debug=True)