from urllib.request import urlopen, Request
from urllib.parse import urlencode
from datetime import datetime

def get_pems_timeseries_report(
        phpsessid: str,
        station_id: str,
        start_time: datetime,
        end_time: datetime,
        query_for: str = "flow",
        query_for_two: str | None = None,
        ):
    """
    Using the Performance Measurement System (PeMS), this function will
    pull data about the flow of traffic at a given station. 

    @Input
    station_id: station_id where you want to capture data
    start_time: point in time to begin fetching data
    stop_time: point in time to stop fetching data
    query_for: type of query desired (ie, flow, occupancy, speed, etc)
    query_for_two: same as query_for; just allows for a second column of data
                   if desired :)
    """

    # Get unix timestamps of start and end time

    start_time_unix, end_time_unix = int(start_time.timestamp()), int(end_time.timestamp())

    ref_loc = f"https://udot.iteris-pems.com/?report_form=1&dnode=VDS&content=loops&export=&station_id={station_id}&s_time_id={start_time_unix}&e_time_id={end_time_unix}&tod=all&tod_from=0&tod_to=0&dow_0=on&dow_1=on&dow_2=on&dow_3=on&dow_4=on&dow_5=on&dow_6=on&holidays=on&q={query_for}&q2={query_for_two if query_for_two else ""}&gn=hour&agg=on&html.x=66&html.y=5"
    cookie = f"PHPSESSID={phpsessid}"

    # Prepare query parameters
    params = {
        "report_form": "1",
        "dnode": "VDS",
        "content": "loops",
        "export": "text",
        "station_id": station_id,
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
        "Upgrade-Insecure-Requests": 1,
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
    with urlopen(req) as res:
        decoded = res.read().decode('utf-8')
        print(decoded)
    return decoded

if __name__ == "__main__":
    get_pems_timeseries_report("3fccfd59b72f5784ae8262c7492b6d51","993103220", datetime(2024, 10, 1), datetime(2024, 10, 2))
