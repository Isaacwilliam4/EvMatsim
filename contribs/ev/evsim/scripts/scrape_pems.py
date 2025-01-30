from urllib.request import urlopen, Request
import requests
from urllib.parse import urlencode
from datetime import datetime
import pandas as pd
import io

def get_pems_timeseries_report(
        phpsessid: str,
        sensor_id: str,
        data_type: str,
        start_time: datetime,
        end_time: datetime,
        query_for: str = "flow",
        query_for_two: str | None = None,
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

    start_time_unix, end_time_unix = int(start_time.timestamp()), int(end_time.timestamp())

    ref_loc = f"https://udot.iteris-pems.com/?report_form=1&dnode=VDS&content=loops&export=&station_id={sensor_id}&s_time_id={start_time_unix}&e_time_id={end_time_unix}&tod=all&tod_from=0&tod_to=0&dow_0=on&dow_1=on&dow_2=on&dow_3=on&dow_4=on&dow_5=on&dow_6=on&holidays=on&q={query_for}&q2={query_for_two if query_for_two else ""}&gn=hour&agg=on&html.x=66&html.y=5"
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
        "TE": "trailers"
    }
    base_url = "https://udot.iteris-pems.com/"
    url_query = urlencode(params)
    full_url = f"{base_url}?{url_query}"
    req = Request(full_url, headers=headers)


    if data_type == "text":
        with urlopen(req) as res:
            decoded = res.read().decode('utf-8')
            print(decoded)
        return decoded


    elif data_type == "xls":
        res = requests.get(full_url, stream=True, headers=headers)
        df = pd.read_excel(io.BytesIO(res.content))
        print(df)
        return df

def aggregate_flow_sensor_data(
        phpsessid: str,
        sensor_id: str,
        start_time: datetime,
        end_time: datetime):
    """
    This will use the get_pems_timeseries_report to grab sensor data 
    and then produce an average at each hour. After grabbing the data
    computes the average flow at each hour and spits out a dataframe
    which contains the sensor and its associated flow values at each
    hour.
    """
    data = get_pems_timeseries_report(phpsessid,
                               sensor_id,
                               'xls',
                               start_time, 
                               end_time
                               )


if __name__ == "__main__":
    aggregate_flow_sensor_data("df4b7491da02a45e3cdf5230cbb97824",
                               "993103220", 
                               datetime(2024, 10, 1), 
                               datetime(2024, 10, 2)
                               )
