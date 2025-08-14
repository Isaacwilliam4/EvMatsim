from urllib.request import urlopen, Request
import requests
from urllib.parse import urlencode
from datetime import datetime
import pandas as pd
import io
from tqdm import tqdm
import json
from sensors import sensors, sensors_subset


def get_pems_timeseries_report(
    phpsessid: str,
    sensor_id: str,
    start_time: datetime,
    end_time: datetime,
    data_type: str = "xls",
    query_for: str = "flow",
    query_for_two: str | None = None,
    verbose: bool = False,
):
    """
    Using the Performance Measurement System (PeMS), this function will
    pull data about the flow of traffic at a given station.

    @Input
    phpsessid: session ID for logging into PeMS. Can be found by inspecting header of request to PeMS.
    sensor_id: sensor_id where you want to capture data
    start_time: point in time to begin fetching data
    stop_time: point in time to stop fetching data
    query_for: type of query desired (ie, flow, occupancy, speed, etc)
    query_for_two: same as query_for; just allows for a second column of data
                   if desired :)
    """

    # Get unix timestamps of start and end time
    start_time_unix, end_time_unix = (
        int(start_time.timestamp()),
        int(end_time.timestamp()),
    )

    ref_loc = f"https://udot.iteris-pems.com/?report_form=1&dnode=VDS&content=loops&export=&station_id={sensor_id}&s_time_id={start_time_unix}&e_time_id={end_time_unix}&tod=all&tod_from=0&tod_to=0&dow_0=on&dow_1=on&dow_2=on&dow_3=on&dow_4=on&dow_5=on&dow_6=on&holidays=on&q={query_for}&q2={query_for_two if query_for_two else ''}&gn=hour&agg=on&html.x=66&html.y=5"
    cookie = f"PHPSESSID={phpsessid}"

    # Prepare query parameters
    params = {
        "report_form": "1",
        "dnode": "VDS",
        "content": "loops",
        "export": data_type,
        "station_id": sensor_id,
        "s_time_id": start_time_unix,
        "e_time_id": end_time_unix,
        "tod": "all",
        "tod_from": "0",
        "tod_to": "0",
        "dow_0": "on",
        "dow_1": "on",
        "dow_2": "on",
        "dow_3": "on",
        "dow_4": "on",
        "dow_5": "on",
        "dow_6": "on",
        "holidays": "on",
        "q": "flow",
        "q2": "",
        "gn": "hour",
        "agg": "on",
    }

    # Prepare request headers
    headers = {
        "Host": "udot.iteris-pems.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
        "Accept": "text/html",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": ref_loc,
        "Connection": "keep-alive",
        "Cookie": cookie,
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

    base_url = "https://udot.iteris-pems.com/"
    url_query = urlencode(params)
    full_url = f"{base_url}?{url_query}"

    if verbose:
        print(f"Request URL: {full_url}")

    # Request to PeMS made here
    req = Request(full_url, headers=headers)

    if data_type == "text":
        with urlopen(req) as res:
            decoded = res.read().decode("utf-8")
            if verbose:
                print(decoded)
        return decoded

    elif data_type == "xls":
        res = requests.get(full_url, stream=True, headers=headers)
        df = pd.read_excel(io.BytesIO(res.content))
        if verbose:
            print(df)
        return df

    else:
        print("ERROR: The requested data type must be 'xls' (excel) or 'text'")
        return pd.DataFrame()  # Give an empty dataframe


def average_flow_per_hour(
    phpsessid: str,
    sensor_id: str,
    start_time: datetime,
    end_time: datetime,
    verbose: bool = False,
):
    """
    use the get_pems_timeseries_report to grab sensor data and then
    produce an average at each hour. After grabbing the data computes
    the average flow at each hour and spits out a dataframe which
    contains the sensor and its associated flow values at each hour.
    """

    # Get a years worth of censor data using scraper
    data = get_pems_timeseries_report(phpsessid, sensor_id, start_time, end_time)

    # Convert date portion of dataframe to hour
    data["Hour"] = data["Hour"].dt.hour

    if verbose:
        print(data)

    # merge rows on hour taking average of other columns
    averages = data.groupby(["Hour"]).mean()

    if verbose:
        print(averages)

    average_hours = averages["Flow (Veh/Hour)"].tolist()

    if verbose:
        print(average_hours)

    return average_hours


def get_all_sensor_averages(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    is_test: bool = False,
):
    """
    finds average flow for all sensors in the sensors.py file
    sticks them all in a dataframe, and then dumps that dataframe to
    a json object.
    """
    flows_per_sensor = {}

    if is_test:
        print("USING TEST SENSOR SUBSET")
        for sensor in sensors_subset:
            flows_per_sensor[sensor] = average_flow_per_hour(
                user_id, str(sensor), start_date, end_date
            )
    else:
        for sensor in tqdm(sensors):
            flows_per_sensor[sensor] = average_flow_per_hour(
                user_id, str(sensor), start_date, end_date
            )

    print(flows_per_sensor)

    return flows_per_sensor


if __name__ == "__main__":
    all_sensors = get_all_sensor_averages(
        "723e2cb1406c352f5d818d14fb56dff8",
        datetime(2024, 1, 1),
        datetime(2025, 1, 1),
        is_test=False,
    )

    with open("sensor_flows.json", "w+") as file:
        json.dump(all_sensors, file)

    print("All flows computed!")
