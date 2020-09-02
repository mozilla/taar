# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
from flask import Flask
from dockerflow.flask import Dockerflow
import optparse
from decouple import config
import importlib
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration


app = Flask(__name__)
dockerflow = Dockerflow(app)

# Hook the application plugin and configure it
PLUGIN = config("TAAR_API_PLUGIN", default=None)


sentry_sdk.init(
    dsn=config("SENTRY_DSN", ""), integrations=[FlaskIntegration()],
)

# There should only be a single registered app for the taar-api
if PLUGIN is None:
    sys.stderr.write("No plugin is defined.\n")
    sys.exit(1)


# Load the function and configure the application
sys.stdout.write("Loading [{}]\n".format(PLUGIN))

plugin_module = importlib.import_module(PLUGIN)
configure_plugin = importlib.import_module(PLUGIN).configure_plugin
APP_WRAPPER = configure_plugin(app)


def flaskrun(app, default_host="127.0.0.1", default_port="8000"):
    """
    Takes a flask.Flask instance and runs it. Parses
    command-line flags to configure the app.
    """

    # Set up the command-line options
    parser = optparse.OptionParser()
    parser.add_option(
        "-H",
        "--host",
        help="Hostname of the Flask app " + "[default %s]" % default_host,
        default=default_host,
    )
    parser.add_option(
        "-P",
        "--port",
        help="Port for the Flask app " + "[default %s]" % default_port,
        default=default_port,
    )

    # Two options useful for debugging purposes, but
    # a bit dangerous so not exposed in the help message.
    parser.add_option(
        "-d", "--debug", action="store_true", dest="debug", help=optparse.SUPPRESS_HELP
    )
    parser.add_option(
        "-p",
        "--profile",
        action="store_true",
        dest="profile",
        help=optparse.SUPPRESS_HELP,
    )

    options, _ = parser.parse_args()

    # If the user selects the profiling option, then we need
    # to do a little extra setup
    if options.profile:
        from werkzeug.contrib.profiler import ProfilerMiddleware

        app.config["PROFILE"] = True
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
        options.debug = True

    app.run(debug=options.debug, host=options.host, port=int(options.port))


if __name__ == "__main__":
    flaskrun(app)
