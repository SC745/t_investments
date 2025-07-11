import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, _dash_renderer, ctx, ALL, dcc, MATCH
from dash.exceptions import PreventUpdate
from pandas.api.types import is_datetime64tz_dtype

import os
import pytz
import json

from dateutil import tz
from dateutil.relativedelta import relativedelta
from datetime import datetime

import dotenv
import pandas as pd
import numpy as np

from tinkoff.invest import Client, InstrumentIdType
from tinkoff.invest.constants import INVEST_GRPC_API_SANDBOX
from tinkoff.invest.utils import now

dotenv.load_dotenv()
TOKEN = os.getenv("INVEST_TOKEN")


#Кодировка для json
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)



#Получить временные интервалы для акции
def get_time_intervals(figi):
    time_intervals = [
        {"label": "Час", "value": "3600", "start_date": None},
        {"label": "4 часа", "value": "14400", "start_date": None},
        {"label": "Сутки", "value": "86400", "start_date": None},
        {"label": "Неделя", "value": "604800", "start_date": None},
        {"label": "Месяц", "value": "2419200", "start_date": None},
        {"label": "Год", "value": "31536000", "start_date": None},
        {"label": "Все время", "value": "3153600000", "start_date": None},
    ]

    share = get_share(figi)

    start_timestamp = share.first_1min_candle_date.timestamp()
    now_timestamp = datetime.now().timestamp()
    life_time = now_timestamp - start_timestamp

    for interval in time_intervals:
        if life_time < int(interval["value"]): interval["start_date"] = datetime.fromtimestamp(start_timestamp).replace(tzinfo=pytz.UTC)
        else: interval["start_date"] = datetime.fromtimestamp(now_timestamp - int(interval["value"])).replace(tzinfo=pytz.UTC)

    return time_intervals

#Получить акцию по figi
def get_share(figi):
    with Client(TOKEN, target=INVEST_GRPC_API_SANDBOX) as client:
        share = client.instruments.share_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI, id=figi)
        return share.instrument
    
#Математическое округление
def math_round(number, precision):
    direction = 1 if number > 0 else -1
    dimension = round(pow(0.1, precision + 1), precision + 1)

    digit = abs(int(number * (1 / dimension))) % 10

    if digit < 5: number -= dimension * digit * direction
    else: number += dimension * (10 - digit) * direction

    return round(number, precision)

#Выгрузить список всех акций в Excel
def shares_to_excel():
    with Client(TOKEN, target=INVEST_GRPC_API_SANDBOX) as client:
        shares_df = pd.DataFrame([vars(share) for share in client.instruments.shares().instruments])

        for col in shares_df:
            if is_datetime64tz_dtype(shares_df[col]):
                shares_df[col] = shares_df[col].dt.tz_localize(None)

        shares_df.to_excel("shares_tmp.xlsx")
        print(shares_df.info())

#Получить акции, доступные для торговли
def get_available_shares():
    with Client(TOKEN, target=INVEST_GRPC_API_SANDBOX) as client:
        shares_df = pd.DataFrame([vars(share) for share in client.instruments.shares().instruments])
        for col in shares_df:
            if is_datetime64tz_dtype(shares_df[col]):
                shares_df[col] = shares_df[col].dt.tz_localize(None)

        shares_df = shares_df.loc[(shares_df["buy_available_flag"] == shares_df["sell_available_flag"]) & shares_df["buy_available_flag"]]

    return shares_df

#Сформировать данные выпадающего списка акций
def get_share_selectdata():  
    shares_df = get_available_shares()

    selectdata = []
    for index, row in shares_df.iterrows():
        data = {}
        data["value"] = row["figi"]
        data["label"] = f"{row['name']} ({row['ticker']})"

        selectdata.append(data)

    return selectdata

#Получить данные для графика
def get_chart_data(figi, candle_interval, time_interval, end_datetime = None):
    if end_datetime == None: end_datetime = datetime.utcnow().replace(tzinfo=pytz.UTC)
    start_datetime = end_datetime - time_interval

    chart_data = []
    with Client(TOKEN) as client: 
        candles = client.get_all_candles(figi=figi, from_=start_datetime, to=end_datetime, interval=candle_interval)
        for candle in candles:
            candle_data = {}
            candle_data["datetime"] = utc_to_local(candle.time, "Russia/Moscow").strftime("%d %b %Y %H:%M")
            candle_data["price"] = quotation_to_float(candle.open)
            candle_data["delta"] = (quotation_to_float(candle.close) - quotation_to_float(candle.open)) / quotation_to_float(candle.high) * 100
            chart_data.append(candle_data)

    return chart_data

#Преобразовать quotation во float
def quotation_to_float(quotation):
    return quotation.units + math_round(quotation.nano / pow(10, 9), 9)

def utc_to_local(utc_dt, timezone):
    local_tz = tz.gettz(timezone)
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt

def local_to_utc(local_dt):
    return local_dt.astimezone(pytz.utc)

#Получить разницу по периоду
def get_delta_string(start_price, end_price, unit):
    precision = max(len(str(start_price).split(".")[-1]), len(str(end_price).split(".")[-1]))
    abs_delta = math_round(abs(end_price - start_price), precision)
    rel_delta = math_round((abs_delta / start_price) * 100, 2)
    delta_string = str(abs_delta) + unit + " | " + str(rel_delta) + "%"

    if start_price < end_price: delta_string = "+" + delta_string
    elif start_price > end_price: delta_string = "-" + delta_string

    return delta_string

#Получить цвет текста разницы
def get_delta_color(delta_string):
    if delta_string[0] == "-": return "red.7"
    elif delta_string[0] == "+": return "green.7"
    
    return "black"



    

