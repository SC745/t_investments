import dash
import dash_mantine_components as dmc
from dash import _dash_renderer

import os
import dotenv
from flask import Flask

dotenv.load_dotenv()
_dash_renderer._set_react_version("18.2.0")

server = Flask(__name__)

app = dash.Dash(
    server=server,
    url_base_pathname='/',
    suppress_callback_exceptions=True,
    title='T-Investments',
    use_pages=True,
    pages_folder='pages',
    external_stylesheets=dmc.styles.ALL
)

server.config.update(SECRET_KEY=os.getenv("SECRET_KEY"))

if __name__ == '__main__':
    server.run(debug=True,port=9662,use_reloader=True, host = "0.0.0.0")
