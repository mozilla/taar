# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from decouple import config
from flask import request
import json

# TAAR specific libraries
from taar.context import default_context
from taar.profile_fetcher import ProfileFetcher
from taar import recommenders

# These are configurations that are specific to the TAAR library
TAAR_MAX_RESULTS = config("TAAR_MAX_RESULTS", default=10, cast=int)


class ResourceProxy(object):
    def __init__(self):
        self._resource = None

    def setResource(self, rsrc):
        self._resource = rsrc

    def getResource(self):
        return self._resource


PROXY_MANAGER = ResourceProxy()


def configure_plugin(app):  # noqa: C901
    """
    This is a factory function that configures all the routes for
    flask given a particular library.
    """
    @app.route('/api/recommendations/<uuid:uuid_client_id>/')
    def recommendations(uuid_client_id):
        """Return a list of recommendations provided a telemetry client_id."""
        # Use the module global PROXY_MANAGER
        global PROXY_MANAGER

        # Coerce the uuid.UUID type into a string
        client_id = str(uuid_client_id)

        branch = request.args.get("branch", "")

        extra_data = {"branch": branch}

        locale = request.args.get("locale", None)
        if locale is not None:
            extra_data["locale"] = locale

        platform = request.args.get("platform", None)
        if platform is not None:
            extra_data["platform"] = platform

        if PROXY_MANAGER.getResource() is None:
            ctx = default_context()
            profile_fetcher = ProfileFetcher(ctx)

            ctx["profile_fetcher"] = profile_fetcher

            # Lock the context down after we've got basic bits installed
            root_ctx = ctx.child()
            r_factory = recommenders.RecommenderFactory(root_ctx)
            root_ctx["recommender_factory"] = r_factory
            instance = recommenders.RecommendationManager(root_ctx.child())
            PROXY_MANAGER.setResource(instance)

        instance = PROXY_MANAGER.getResource()
        recommendations = instance.recommend(
            client_id=client_id, limit=TAAR_MAX_RESULTS, extra_data=extra_data
        )

        # Strip out weights from TAAR results to maintain compatibility
        # with TAAR 1.0
        jdata = {"results": [x[0] for x in recommendations]}

        response = app.response_class(
            response=json.dumps(jdata), status=200, mimetype="application/json"
        )
        return response

    class MyPlugin:
        def set(self, config_options):
            """
            This setter is primarily so that we can instrument the
            cached RecommendationManager implementation under test.

            All plugins should implement this set method to enable
            overwriting configuration options with a TAAR library.
            """
            global PROXY_MANAGER
            if "PROXY_RESOURCE" in config_options:
                PROXY_MANAGER._resource = config_options["PROXY_RESOURCE"]

    return MyPlugin()
