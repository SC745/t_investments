import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, _dash_renderer, ctx, ALL, dcc, MATCH
from dash.exceptions import PreventUpdate
from flask import session

import os
import json

from dateutil.relativedelta import relativedelta
from datetime import datetime
import functions

import dotenv
import pandas as pd
import numpy as np
from dash_iconify import DashIconify

from tinkoff.invest import CandleInterval

dotenv.load_dotenv()
TOKEN = os.getenv("INVEST_TOKEN")

_dash_renderer._set_react_version("18.2.0")
dash.register_page(__name__)

time_interval_props = {
    "1d": {"time_interval": relativedelta(days = 1), "candle_interval": CandleInterval.CANDLE_INTERVAL_1_MIN},
    "1w": {"time_interval": relativedelta(weeks = 1), "candle_interval": CandleInterval.CANDLE_INTERVAL_5_MIN},
    "1m": {"time_interval": relativedelta(months = 1), "candle_interval": CandleInterval.CANDLE_INTERVAL_30_MIN},
    "6m": {"time_interval": relativedelta(months = 6), "candle_interval": CandleInterval.CANDLE_INTERVAL_2_HOUR},
    "1y": {"time_interval": relativedelta(years = 1), "candle_interval": CandleInterval.CANDLE_INTERVAL_4_HOUR},
}


def layout():
    layout = dmc.Box(
        children = [
            dcc.Interval(id = "load_interval", n_intervals = 0, max_intervals = 1, interval = 1),
            dmc.Box(
                children = [
                    dmc.Flex(
                        children = [
                            dmc.Select(id = "share_select", label = "Акция", clearable = True, searchable = True, w = 300),
                            dmc.Select(id = "interval_select", label = "Временной промежуток"),
                            dmc.ActionIcon(id = {"type": "nav_button", "index": "first"}, children = DashIconify(icon = "mingcute:arrows-left-fill", width = 20), size = "input-sm"),
                            dmc.ActionIcon(id = {"type": "nav_button", "index": "prev"}, children = DashIconify(icon = "mingcute:left-fill", width = 20), size = "input-sm"),
                            dmc.ActionIcon(id = {"type": "nav_button", "index": "refresh"}, children = DashIconify(icon = "mingcute:refresh-3-fill", width = 20), size = "input-sm"),
                            dmc.ActionIcon(id = {"type": "nav_button", "index": "next"}, children = DashIconify(icon = "mingcute:right-fill", width = 20), size = "input-sm"),
                            dmc.ActionIcon(id = {"type": "nav_button", "index": "last"}, children = DashIconify(icon = "mingcute:arrows-right-fill", width = 20), size = "input-sm"),
                        ],
                        gap = "md",
                        align="flex-end"
                    ),
                    dmc.Box(
                        id = "price_delta",
                        children = [
                            dmc.Text(children = "", fz = "sm", fw = 500),
                            dmc.Text(children = "", fz = "h2", fw = 650, ta = "right"),
                        ],
                        pt = 2
                    )
                ],
                style = {"display":"flex", "justify-content":"space-between"},
                pt = "md",
                px = "md"
            ),
            dmc.Box(
                children = [
                    dmc.LineChart(
                        id = "share_price_chart",
                        dataKey = "datetime",
                        data = [],
                        series = [
                            {"name": "price", "color": "indigo.6"},
                        ],
                        curveType = "linear",
                        tickLine = "xy",
                        gridAxis = "none",
                        withXAxis = False,
                        withYAxis = False,
                        withDots = False,
                        unit = "₽",
                        pt = "md",
                        px = "md",
                        h = 350
                    ),
                    dmc.RangeSlider(
                        id = "share_price_slider",
                        min = 0,
                        step = 1,
                        minRange = 1,
                        label = None,
                        pushOnOverlap = False,
                        color = "gray.3",
                        pt = 0,
                        px = "md",
                    ),
                ],
            )
        ],
    )

    layout = dmc.MantineProvider(layout)
    return layout


@dash.callback(
    output = {
        "select_data": {
            "share": Output("share_select", "data"),
            "interval": Output("interval_select", "data"),
        },
        "select_value": {
            "share": Output("share_select", "value"),
            "interval": Output("interval_select", "value"),
        },
    },
    inputs = {
        "input": {
            "load_interval": Input("load_interval", "n_intervals"),
        }
    },
    prevent_initial_call = True
)
def initial_callback(input):
    output = {}

    output["select_data"] = {}
    output["select_data"]["share"] = functions.get_share_selectdata()
    output["select_data"]["interval"] = [
        {"label": "День", "value": "1d"},
        {"label": "Неделя", "value": "1w"},
        {"label": "Месяц", "value": "1m"},
        {"label": "6 месяцев", "value": "6m"},
        {"label": "Год", "value": "1y"},
    ]

    output["select_value"] = {}
    output["select_value"]["share"] = output["select_data"]["share"][0]["value"]
    output["select_value"]["interval"] = "1m"

    return output


@dash.callback(
    output = {
        "chart_data": Output("share_price_chart", "data"),
        "nav_buttons_states": {
            "first": Output({"type": "nav_button", "index": "first"}, "disabled"),
            "prev": Output({"type": "nav_button", "index": "prev"}, "disabled"),
            "next": Output({"type": "nav_button", "index": "next"}, "disabled"),
            "last": Output({"type": "nav_button", "index": "last"}, "disabled"),
        }
    },
    inputs = {
        "input": {
            "select_value": {
                "share": Input("share_select", "value"),
                "interval": Input("interval_select", "value"),
            },
            "nav_buttons": {
                "first": Input({"type": "nav_button", "index": "first"}, "n_clicks"),
                "prev": Input({"type": "nav_button", "index": "prev"}, "n_clicks"),
                "refresh": Input({"type": "nav_button", "index": "refresh"}, "n_clicks"),
                "next": Input({"type": "nav_button", "index": "next"}, "n_clicks"),
                "last": Input({"type": "nav_button", "index": "last"}, "n_clicks"),
            },
            "chart_data": State("share_price_chart", "data"),
        }
    },
    prevent_initial_call = True
)
def update_chart_data(input):
    if not (input["select_value"]["share"] and input["select_value"]["interval"]): raise PreventUpdate

    time_interval = time_interval_props[input["select_value"]["interval"]]["time_interval"]
    dt_now = functions.local_to_utc(datetime.now())
    start_dt = functions.get_share(input["select_value"]["share"]).first_1min_candle_date
    end_dt = dt_now

    if not isinstance(ctx.triggered_id, str) and ctx.triggered_id["type"] == "nav_button":
        end_dt = functions.local_to_utc(datetime.strptime(input["chart_data"][-1]["datetime"], "%d %b %Y %H:%M"))
        if ctx.triggered_id["index"] == "refresh": end_dt = dt_now
        if ctx.triggered_id["index"] == "first": end_dt = start_dt + time_interval
        if ctx.triggered_id["index"] == "last": end_dt = dt_now
        if ctx.triggered_id["index"] == "prev": end_dt = start_dt + time_interval if end_dt - time_interval < start_dt else end_dt - time_interval
        if ctx.triggered_id["index"] == "next": end_dt = dt_now if end_dt + time_interval > dt_now else end_dt + time_interval

    output = {}
    output["nav_buttons_states"] = {}
    output["nav_buttons_states"]["next"] = output["nav_buttons_states"]["last"] = bool(end_dt >= dt_now)
    output["nav_buttons_states"]["prev"] = output["nav_buttons_states"]["first"] = bool(end_dt - time_interval <= start_dt)
    output["chart_data"] = functions.get_chart_data(input["select_value"]["share"], time_interval_props[input["select_value"]["interval"]]["candle_interval"], time_interval, end_dt)

    return output


@dash.callback(
    Output("share_price_slider", "max"),
    Output("share_price_slider", "value"),
    Output("share_price_chart", "yAxisProps"),
    Output("share_price_chart", "referenceLines", allow_duplicate = True),
    
    Input("share_price_chart", "data"),
    State("share_price_chart", "referenceLines"),
    prevent_initial_call = True
)
def update_chart_props(chart_data, referenceLines):

    slider_max = len(chart_data) - 1
    slider_value = [0, slider_max]

    df = pd.DataFrame(chart_data)
    yAxisProps = {"domain": [df["price"].min(), df["price"].max()], "padding": {"top": 20, "bottom": 20}}

    referenceLines_output = []
    if referenceLines:
        for line in referenceLines:
            if "x" in line: referenceLines_output.append(line)

    referenceLines_output += [
        {"y": df["price"].min(), "label": df["price"].min()},
        {"y": df["price"].max(), "label": df["price"].max()}
    ]

    return slider_max, slider_value, yAxisProps, referenceLines_output


@dash.callback(
    Output("price_delta", "children"),
    Output("share_price_chart", "referenceLines", allow_duplicate = True),
    
    Input("share_price_slider", "value"),
    State("share_price_chart", "data"),
    State("share_price_chart", "referenceLines"),
    prevent_initial_call = True
)
def slider_change_processing(slider_value, chart_data, referenceLines):

    date_interval = chart_data[slider_value[0]]["datetime"] + " - " + chart_data[slider_value[1]]["datetime"]
    delta_string = functions.get_delta_string(chart_data[slider_value[0]]["price"], chart_data[slider_value[1]]["price"], "₽")
    delta_color = functions.get_delta_color(delta_string)

    price_delta_info = []
    price_delta_info.append(dmc.Text(children = date_interval, fz = "sm", fw = 500))
    price_delta_info.append(dmc.Text(children = delta_string, fz = "h2", fw = 650, c = delta_color, ta = "right"))

    referenceLines_output = []
    for line in referenceLines:
        if "y" in line: referenceLines_output.append(line)

    referenceLines_output += [
        {"x": chart_data[slider_value[0]]["datetime"]},
        {"x": chart_data[slider_value[1]]["datetime"]}
    ]

    return price_delta_info, referenceLines_output



    
    












