import requests
from bs4 import BeautifulSoup
from sensors import sensors, sensors_subset
import re
import json
from tqdm import tqdm


def get_sensor_lat_long(sensor, user_id):
    """
    Gets the lat and long of a censor from the UDOT PeMS traffic statistics
    service. A list of all sensors at the time of authoring (Jan 30, 2025)
    is available in sensors.py.

    @Input
    sensor - the sensor which you would like the lat/long of. Full list of sensors
             available at https://udot.iteris-pems.com/?dnode=State&content=elv&tab=stations&pagenum_all=1
    user_id - Your authentication token for accessing the UDOT PeMS service. Can be found by inspecting the page
              and looking at your request header for the "Cookie" parameter.
    """

    def base_url(sensor_id):
        return f"https://udot.iteris-pems.com/?pagenum_all=1&station_id={sensor_id}&dnode=VDS"

    def cookie(phpsessid):
        return f"PHPSESSID={phpsessid}"

    headers = {
        "Host": "udot.iteris-pems.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://udot.iteris-pems.com/?dnode=State&content=elv&tab=stations&pagenum_all=1",
        "Connection": "keep-alive",
        "Cookie": cookie(user_id),
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Priority": "u=0, i",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "TE": "trailers",
    }

    res = requests.get(base_url(sensor), headers=headers)

    if res.status_code != 200:
        print("Failed to retreive page. Perhaps your Cookie has expired?")
        exit(1)

    soup = BeautifulSoup(res.text, "html.parser")

    scripts = soup.find_all(string=re.compile("var thumbMap    ="))

    # Extract only the floats inside "center":[...]
    match = re.search(r'"center":\["(-?\d+\.\d+)","(-?\d+\.\d+)"\]', scripts[0])

    if match:
        lat, lon = match.groups()
        lat, lon = float(lat), float(lon)
        return lat, lon
    else:
        print("Not found")


def get_all_sensor_locations(user_id, is_test=False):
    locations = {}
    if is_test:
        for sensor in tqdm(sensors_subset):
            locations[sensor] = get_sensor_lat_long(sensor, user_id)
    else:
        for sensor in tqdm(sensors):
            locations[sensor] = get_sensor_lat_long(sensor, user_id)

    return locations


if __name__ == "__main__":
    all_locations = get_all_sensor_locations("3fccfd59b72f5784ae8262c7492b6d51")

    with open("sensor_locations.json", "w+") as file:
        json.dump(all_locations, file)

    print("All locations grabbed")
