from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

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
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

# Home route to display the webpage
@app.route("/")
def home():
    return render_template("index.html")

# API endpoint to get earthquake data
@app.route("/get_earthquakes", methods=["POST"])
def get_earthquakes():
    data = request.json  # Get JSON data from the frontend form
    result = fetch_earthquake_data(
        data["start_date"], data["end_date"],
        data["min_magnitude"], data["max_magnitude"],
        data["min_lat"], data["max_lat"],
        data["min_lon"], data["max_lon"]
    )
    return jsonify(result)  # Return JSON response

if __name__ == "__main__":
    app.run(debug=True)
