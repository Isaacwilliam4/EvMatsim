import json
import csv


def create_sensor_csv(flows_path: str, locations_path: str, out_path: str) -> None:
    with open(flows_path, "r") as sensor_flows:
        flows = json.load(sensor_flows)

    with open(locations_path, "r") as sensor_locations:
        locations = json.load(sensor_locations)

    # Write to CSV
    with open(out_path, mode="w", newline="") as file:
        writer = csv.writer(file)

        # Write header
        header = ["sensor_id", "latitude", "longitude"] + [
            f"flow_{hour}" for hour in range(1, 25)
        ]
        writer.writerow(header)

        # Write sensor data
        for sensor_id, coords in locations.items():
            lat, lon = coords
            flow = flows.get(sensor_id, [0] * 24)  # Default to zero flows if missing
            writer.writerow([sensor_id, lat, lon] + flow)


if __name__ == "__main__":
    create_sensor_csv("sensor_flows.json", "sensor_locations.json", "sensor_data.csv")
