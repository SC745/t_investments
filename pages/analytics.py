import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, _dash_renderer, ctx, ALL, dcc, MATCH, callback
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify

import plotly.figure_factory as ff

from flask import session

import os
import json
import dotenv

from dateutil.relativedelta import relativedelta
from datetime import datetime

import pandas as pd
import numpy as np

from tinkoff.invest import CandleInterval

import functions

dotenv.load_dotenv()
TOKEN = os.getenv("INVEST_TOKEN")

_dash_renderer._set_react_version("18.2.0")
dash.register_page(__name__)

chart_props = {
    "standard_values": {
        "1d": {"interval": relativedelta(days = 1), "candle": {"interval": CandleInterval.CANDLE_INTERVAL_1_MIN, "value": "1m"}},
        "1w": {"interval": relativedelta(weeks = 1), "candle": {"interval": CandleInterval.CANDLE_INTERVAL_5_MIN, "value": "5m"}},
        "1m": {"interval": relativedelta(months = 1), "candle": {"interval": CandleInterval.CANDLE_INTERVAL_30_MIN, "value": "30m"}},
        "6m": {"interval": relativedelta(months = 6), "candle": {"interval": CandleInterval.CANDLE_INTERVAL_2_HOUR, "value": "2h"}},
        "1y": {"interval": relativedelta(years = 1), "candle": {"interval": CandleInterval.CANDLE_INTERVAL_4_HOUR, "value": "4h"}},
    },
    "candle_intervals": {
        "4h": CandleInterval.CANDLE_INTERVAL_4_HOUR,
        "2h": CandleInterval.CANDLE_INTERVAL_2_HOUR,
        "1h": CandleInterval.CANDLE_INTERVAL_HOUR,
        "30m": CandleInterval.CANDLE_INTERVAL_30_MIN,
        "15m": CandleInterval.CANDLE_INTERVAL_15_MIN,
        "5m": CandleInterval.CANDLE_INTERVAL_5_MIN,
        "3m": CandleInterval.CANDLE_INTERVAL_3_MIN,
        "2m": CandleInterval.CANDLE_INTERVAL_2_MIN,
        "1m": CandleInterval.CANDLE_INTERVAL_1_MIN,
    }
}


def layout():
    dmc.add_figure_templates()
    layout = dmc.Box(
        children = [
            dcc.Interval(id = "load_interval", n_intervals = 0, max_intervals = 1, interval = 1),
            dmc.Box(
                children = [
                    dmc.Flex(
                        children = [
                            dmc.Select(id = {"type": "select", "index": "share"}, label = "Акция", clearable = True, searchable = True, w = 300),
                            dmc.Select(id = {"type": "select", "index": "interval"}, label = "Временной промежуток"),
                            dmc.Select(id = {"type": "select", "index": "candle"}, label = "Интервал свечи"),
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
            dmc.Tabs(
                children = [
                    dmc.TabsList(
                        children = [
                            dmc.TabsTab("Курс", value = "course", leftSection = DashIconify(icon="mingcute:chart-line-fill")),
                            dmc.TabsTab("Распределение", value = "distribution", leftSection = DashIconify(icon="mingcute:chart-bar-line")),
                            dmc.TabsTab("Корреляция", value = "correlation", leftSection = DashIconify(icon="mingcute:chart-bar-line")),
                            dmc.TabsTab("Настройки", value = "settings", leftSection = DashIconify(icon="mingcute:settings-3-line")),
                        ],
                        px = "md",
                    ),
                    dmc.TabsPanel(
                        children = [
                            dmc.LineChart(
                                id = "price_chart",
                                dataKey = "datetime",
                                data = [],
                                series = [
                                    {"name": "open", "color": "blue.7"},
                                    {"name": "balance", "color": "red.7", "yAxisId": "right"},
                                    #{"name": "vector", "color": "green.7"},
                                ],
                                curveType = "linear",
                                tickLine = "xy",
                                gridAxis = "none",
                                withXAxis = False,
                                withYAxis = False,
                                withDots = False,
                                pt = "md",
                                px = "md",
                                h = 700
                            ),
                            dmc.RangeSlider(
                                id = "share_price_slider",
                                min = 0,
                                step = 1,
                                minRange = 1,
                                label = None,
                                pushOnOverlap = False,
                                color = "gray.3",
                                px = "md",
                            ),
                        ],
                        value = "course"
                    ),
                    dmc.TabsPanel(
                        children = [
                            dmc.Box(
                                children = [
                                    dcc.Graph(id = "dist_chart")
                                ],
                                pt = "md",
                                px = "md",
                            ),
                            
                        ],
                        value = "distribution"
                    ),
                    dmc.TabsPanel(
                        children = [
                            
                        ],
                        value = "correlation"
                    ),
                    dmc.TabsPanel(
                        children = [
                            dmc.Text(children = "График курса", fz = "h3", fw = 500, pb = "md"),
                            dmc.Stack(
                                children = [
                                    dmc.Checkbox(id = "standard_candles", label = "Использовать стандартные свечи"),
                                    dmc.NumberInput(id = "vector_size", label = "Размер вектора", min = 1, max = 10, allowDecimal = False),
                                ],
                                gap = "sm",
                                pb = "md"
                            ),
                            dmc.Text("График распределения", fz = "h3", fw = 500, pb = "md"),
                            dmc.Stack(
                                children = [
                                    dmc.Select(id = {"type": "select", "index": "vector_vals"}, label = "Значения", w = 150),
                                    dmc.Checkbox(id = {"category": "dist_chart_props", "index": "rm_outliers"}, label = "Исключать выбросы"),
                                    dmc.Checkbox(id = {"category": "dist_chart_props", "index": "show_hist"}, label = "Показывать гистограмму"),
                                    dmc.Checkbox(id = {"category": "dist_chart_props", "index": "show_curve"}, label = "Показывать кривую"),
                                    dmc.Checkbox(id = {"category": "dist_chart_props", "index": "show_rug"}, label = "Показывать штрих-диаграмму"),
                                ],
                                gap = "sm",
                                pb = "md"
                            )
                        ],
                        value = "settings",
                        px = "md"
                    )
                ],
                value = "share_price",
                pt = "md",
            ),
        ],
    )

    layout = dmc.MantineProvider(layout)
    return layout



@dash.callback(
    output = {
        "select_data": {
            "share": Output({"type": "select", "index": "share"}, "data"),
            "interval": Output({"type": "select", "index": "interval"}, "data"),
            "candle": Output({"type": "select", "index": "candle"}, "data"),
            "vector_vals": Output({"type": "select", "index": "vector_vals"}, "data"),
        },
        "select_values": {
            "share": Output({"type": "select", "index": "share"}, "value"),
            "interval": Output({"type": "select", "index": "interval"}, "value"),
            "candle": Output({"type": "select", "index": "candle"}, "value", allow_duplicate = True),
            "vector_vals": Output({"type": "select", "index": "vector_vals"}, "value"),
            "vector_size": Output("vector_size", "value"),
        },
        "checkbox_states": {
            "standard_candles": Output("standard_candles", "checked"),
            "distplot_props": Output({"category": "dist_chart_props", "index": ALL}, "checked")
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
    session.clear()
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
    output["select_data"]["candle"] = [
        {"label": "4 часа", "value": "4h"},
        {"label": "2 часа", "value": "2h"},
        {"label": "1 час", "value": "1h"},
        {"label": "30 минут", "value": "30m"},
        {"label": "15 минут", "value": "15m"},
        {"label": "5 минут", "value": "5m"},
        {"label": "3 минуты", "value": "3m"},
        {"label": "2 минуты", "value": "2m"},
        {"label": "1 минута", "value": "1m"},
    ]
    output["select_data"]["vector_vals"] = [
        {"label": "Все", "value": "all"},
        {"label": "Положительные", "value": "positive"},
        {"label": "Отрицательные", "value": "negative"},
    ]

    if not "data" in session:
        session_data = {}

        session_data["select_values"] = {}
        session_data["select_values"]["share"] = output["select_data"]["share"][0]["value"]
        session_data["select_values"]["interval"] = "1m"
        session_data["select_values"]["candle"] = "30m"
        session_data["select_values"]["vector_vals"] = "all"
        session_data["select_values"]["vector_size"] = 1

        session_data["distplot_props"] = {}
        session_data["distplot_props"]["rm_outliers"] = False
        session_data["distplot_props"]["show_hist"] = True
        session_data["distplot_props"]["show_curve"] = True
        session_data["distplot_props"]["show_rug"] = True

        session_data["standard_candles"] = True
    else: session_data = json.loads(session["data"])

    output["checkbox_states"] = {}
    output["checkbox_states"]["standard_candles"] = session_data["standard_candles"]
    output["checkbox_states"]["distplot_props"] = [session_data["distplot_props"][key] for key in session_data["distplot_props"]]

    output["select_values"] = {}
    output["select_values"]["share"] = session_data["select_values"]["share"]
    output["select_values"]["interval"] = session_data["select_values"]["interval"]
    output["select_values"]["candle"] = session_data["select_values"]["candle"]
    output["select_values"]["vector_vals"] = session_data["select_values"]["vector_vals"]
    output["select_values"]["vector_size"] = session_data["select_values"]["vector_size"]

    session["data"] = json.dumps(session_data, cls = functions.NpEncoder)

    return output


@dash.callback(
    output = {
        "price_chart": Output("price_chart", "data"),
        "nav_buttons_states": {
            "first": Output({"type": "nav_button", "index": "first"}, "disabled"),
            "prev": Output({"type": "nav_button", "index": "prev"}, "disabled"),
            "next": Output({"type": "nav_button", "index": "next"}, "disabled"),
            "last": Output({"type": "nav_button", "index": "last"}, "disabled"),
        }
    },
    inputs = {
        "input": {
            "select_values": {
                "share": Input({"type": "select", "index": "share"}, "value"),
                "interval": State({"type": "select", "index": "interval"}, "value"),
                "candle": Input({"type": "select", "index": "candle"}, "value"),
                "vector_size": Input("vector_size", "value"),
            },
            "nav_buttons": Input({"type": "nav_button", "index": ALL}, "n_clicks"),
            "chart_data": State("price_chart", "data"),
        }
    },
    prevent_initial_call = True
)
def update_chart_data(input):
    if not (input["select_values"]["share"] and input["select_values"]["interval"]): raise PreventUpdate

    time_interval = chart_props["standard_values"][input["select_values"]["interval"]]["interval"]
    candle_interval = chart_props["candle_intervals"][input["select_values"]["candle"]]

    dt_now = functions.local_to_utc(datetime.now())
    start_dt = functions.get_share(input["select_values"]["share"]).first_1min_candle_date
    end_dt = dt_now

    if ctx.triggered_id["type"] == "nav_button":
        #Обработка нажатий кнопок верхней панели
        end_dt = functions.local_to_utc(datetime.strptime(input["chart_data"][-1]["datetime"], "%d %b %Y %H:%M"))
        if ctx.triggered_id["index"] == "refresh": end_dt = dt_now
        if ctx.triggered_id["index"] == "first": end_dt = start_dt + time_interval
        if ctx.triggered_id["index"] == "last": end_dt = dt_now
        if ctx.triggered_id["index"] == "prev": end_dt = start_dt + time_interval if end_dt - time_interval < start_dt else end_dt - time_interval
        if ctx.triggered_id["index"] == "next": end_dt = dt_now if end_dt + time_interval > dt_now else end_dt + time_interval
    elif ctx.triggered_id["type"] == "select":
        #Запись в хранилище сессии значений выпадающих списков
        session_data = json.loads(session["data"])
        session_data["select_values"]["share"] = input["select_values"]["share"]
        session_data["select_values"]["candle"] = input["select_values"]["candle"]
        session_data["select_values"]["vector_size"] = input["select_values"]["vector_size"]
        session["data"] = json.dumps(session_data, cls = functions.NpEncoder)

    candles_df = functions.get_candles_df(input["select_values"]["share"], candle_interval, time_interval, end_dt)
    candles_df["vector"] = functions.get_vectors(candles_df, input["select_values"]["vector_size"])

    positive_vectors = candles_df[candles_df["vector"] > 0]["vector"]
    candles_df["balance"] = functions.get_balance_history(candles_df, np.percentile(positive_vectors, 90), 0, 0.0003)

    output = {}
    output["nav_buttons_states"] = {}
    output["nav_buttons_states"]["next"] = output["nav_buttons_states"]["last"] = bool(end_dt >= dt_now)
    output["nav_buttons_states"]["prev"] = output["nav_buttons_states"]["first"] = bool(end_dt - time_interval <= start_dt)
    output["price_chart"] = candles_df.to_dict("records")
    
    return output


@callback(
    Output("share_price_slider", "max"),
    Output("share_price_slider", "value"),
    Output("price_chart", "yAxisProps"),
    Output("price_chart", "rightYAxisProps"),
    Output("price_chart", "referenceLines", allow_duplicate = True),
    
    Input("price_chart", "data"),
    State("price_chart", "referenceLines"),
    prevent_initial_call = True
)
def update_chart_props(chart_data, referenceLines):
    slider_max = len(chart_data) - 1
    slider_value = [0, slider_max]

    df = pd.DataFrame(chart_data)
    yAxisProps = {"domain": [df["open"].min(), df["open"].max()], "padding": {"top": 20, "bottom": 20}}
    rightYAxisProps = {"domain": [df["balance"].min(), df["balance"].max()], "padding": {"top": 20, "bottom": 20}}

    referenceLines_output = []
    if referenceLines:
        for line in referenceLines:
            if "x" in line: referenceLines_output.append(line)

    referenceLines_output += [
        {"y": df["open"].min(), "label": df["open"].min()},
        {"y": df["open"].max(), "label": df["open"].max()}
    ]

    return slider_max, slider_value, yAxisProps, rightYAxisProps, referenceLines_output


@callback(
    Output("price_delta", "children"),
    Output("price_chart", "referenceLines", allow_duplicate = True),
    Output("dist_chart", "figure", allow_duplicate = True),
    #Output("corr_chart", "data"),
    
    Input("share_price_slider", "value"),
    Input({"type": "select", "index": "vector_vals"}, "value"),
    Input({"category": "dist_chart_props", "index": ALL}, "checked"),
    Input({"category": "dist_chart_props", "index": ALL}, "id"),
    State("price_chart", "data"),
    State("price_chart", "referenceLines"),
    State("vector_size", "value"),
    prevent_initial_call = True
)
def slider_change_processing(slider_value, vector_vals, checkbox_states, checkbox_ids, chart_data, referenceLines, vector_size):
    if not slider_value: raise PreventUpdate

    date_interval = chart_data[slider_value[0]]["datetime"] + " - " + chart_data[slider_value[1]]["datetime"]
    delta_string = functions.get_delta_string(chart_data[slider_value[0]]["open"], chart_data[slider_value[1]]["open"], "₽")
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

    candles_df = pd.DataFrame(chart_data)
    candles_df = candles_df[(candles_df.index >= slider_value[0]) & (candles_df.index <= slider_value[1])]
    checkboxes = {id["index"]: state for id, state in zip(checkbox_ids, checkbox_states)}

    if vector_vals == "positive": candles_df = candles_df.loc[candles_df["vector"] > 0]
    if vector_vals == "negative": candles_df = candles_df.loc[candles_df["vector"] < 0]
    if checkboxes["rm_outliers"]: candles_df = functions.remove_outliers(candles_df, "vector")

    fig = ff.create_distplot(
        hist_data = [list(candles_df["vector"])], 
        group_labels = ["vector"], 
        rug_text = [list(candles_df["datetime"])], 
        curve_type = "kde", 
        bin_size = (candles_df["vector"].max() - candles_df["vector"].min()) / 50, 
        show_hist = checkboxes["show_hist"],
        show_curve = checkboxes["show_curve"],
        show_rug = checkboxes["show_rug"],
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend = False, height = 700)

    session_data = json.loads(session["data"])
    for key in checkboxes: session_data["distplot_props"][key] = checkboxes[key]
    session["data"] = json.dumps(session_data, cls = functions.NpEncoder)
    
    return price_delta_info, referenceLines_output, fig


@callback(
    Output({"type": "select", "index": "candle"}, "disabled"),
    Output({"type": "select", "index": "candle"}, "value", allow_duplicate = True),

    Input("standard_candles", "checked"),
    Input({"type": "select", "index": "interval"}, "value"),
    State({"type": "select", "index": "candle"}, "value"),
    prevent_initial_call = True
)
def set_candle(is_standard, interval, old_candle_value):
    if not (interval and old_candle_value): raise PreventUpdate
    candle_select_disabled = is_standard
    if is_standard: new_candle_value = chart_props["standard_values"][interval]["candle"]["value"]
    else: new_candle_value = old_candle_value

    session_data = json.loads(session["data"])
    session_data["select_values"]["candle"] = new_candle_value
    session_data["select_values"]["interval"] = interval
    session["data"] = json.dumps(session_data, cls = functions.NpEncoder)

    return candle_select_disabled, new_candle_value


