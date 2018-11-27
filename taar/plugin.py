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

    @app.route("/v1/api/recommendations/<hashed_client_id>/", methods=["GET", "POST"])
    def recommendations(hashed_client_id):
        """Return a list of recommendations provided a telemetry client_id."""
        # Use the module global PROXY_MANAGER
        global PROXY_MANAGER

        try:
            promoted_guids = []
            if request.method == "POST":
                json_data = request.data
                # At least Python3.5 returns request.data as bytes
                # type instead of a string type.
                # Both Python2.7 and Python3.7 return a string type
                if type(json_data) == bytes:
                    json_data = json_data.decode("utf8")

                post_data = json.loads(json_data)
                promoted_guids = post_data.get("options", {}).get("promoted", [])
                if promoted_guids:
                    promoted_guids.sort(key=lambda x: x[1], reverse=True)
                    promoted_guids = [x[0] for x in promoted_guids]
        except Exception as e:
            return app.response_class(
                response=json.dumps({"error": "Invalid JSON in POST: {}".format(e)}),
                status=400,
                mimetype="application/json",
            )

        # Coerce the uuid.UUID type into a string
        client_id = str(hashed_client_id)

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
        jdata["results"] = (promoted_guids + jdata["results"])[:TAAR_MAX_RESULTS]

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
