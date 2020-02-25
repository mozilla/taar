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


def clean_promoted_guids(raw_promoted_guids):
    """ Verify that the promoted GUIDs are formatted correctly,
    otherwise strip it down into an empty list.
    """
    valid = True

    for row in raw_promoted_guids:
        if len(row) != 2:
            valid = False
            break

        if not (
            (isinstance(row[0], str) or isinstance(row[0], unicode))
            and (isinstance(row[1], int) or isinstance(row[1], float))  # noqa
        ):
            valid = False
            break

    if valid:
        return raw_promoted_guids
    return []


def merge_promoted_guids(promoted_guids, recommended_guids):
    guids = set()
    final = []
    tmp = sorted(
        promoted_guids + [x for x in recommended_guids],
        key=lambda x: x[1],
        reverse=True,
    )
    for guid, weight in tmp:
        if guid not in guids:
            final.append((guid, weight))
            guids.add(guid)
    return final


def configure_plugin(app):  # noqa: C901
    """
    This is a factory function that configures all the routes for
    flask given a particular library.
    """

    @app.route(
        "/v1/api/client_has_addon/<hashed_client_id>/<addon_id>/", methods=["GET"]
    )
    def client_has_addon(hashed_client_id, addon_id):
        # Use the module global PROXY_MANAGER
        global PROXY_MANAGER
        recommendation_manager = check_proxy_manager(PROXY_MANAGER)
        pf = recommendation_manager._ctx.get("profile_fetcher")

        client_meta = pf.get(hashed_client_id)
        if client_meta is None:
            # no valid client metadata was found for the given
            # clientId
            result = {"results": False, 'error': 'No client found'}
            response = app.response_class(
                response=json.dumps(result), status=200, mimetype="application/json"
            )
            return response

        result = {"results": addon_id in client_meta.get("installed_addons", [])}
        response = app.response_class(
            response=json.dumps(result), status=200, mimetype="application/json"
        )
        return response

    @app.route("/v1/api/recommendations/<hashed_client_id>/", methods=["GET", "POST"])
    def recommendations(hashed_client_id):
        """Return a list of recommendations provided a telemetry client_id."""
        # Use the module global PROXY_MANAGER
        global PROXY_MANAGER

        extra_data = {}
        extra_data["options"] = {}
        extra_data["options"]["promoted"] = []

        try:
            if request.method == "POST":
                json_data = request.data
                # At least Python3.5 returns request.data as bytes
                # type instead of a string type.
                # Both Python2.7 and Python3.7 return a string type
                if type(json_data) == bytes:
                    json_data = json_data.decode("utf8")

                if json_data != "":
                    post_data = json.loads(json_data)
                    raw_promoted_guids = post_data.get("options", {}).get(
                        "promoted", []
                    )
                    promoted_guids = clean_promoted_guids(raw_promoted_guids)
                    extra_data["options"]["promoted"] = promoted_guids

        except Exception as e:
            jdata = {}
            jdata["results"] = []
            jdata["error"] = "Invalid JSON in POST: {}".format(e)
            return app.response_class(
                response=json.dumps(jdata, status=400, mimetype="application/json")
            )

        # Coerce the uuid.UUID type into a string
        client_id = str(hashed_client_id)

        locale = request.args.get("locale", None)
        if locale is not None:
            extra_data["locale"] = locale

        platform = request.args.get("platform", None)
        if platform is not None:
            extra_data["platform"] = platform

        recommendation_manager = check_proxy_manager(PROXY_MANAGER)
        recommendations = recommendation_manager.recommend(
            client_id=client_id, limit=TAAR_MAX_RESULTS, extra_data=extra_data
        )

        promoted_guids = extra_data.get("options", {}).get("promoted", [])
        recommendations = merge_promoted_guids(promoted_guids, recommendations)

        # Strip out weights from TAAR results to maintain compatibility
        # with TAAR 1.0
        jdata = {"results": [x[0] for x in recommendations]}

        response = app.response_class(
            response=json.dumps(jdata), status=200, mimetype="application/json"
        )
        return response

    def check_proxy_manager(PROXY_MANAGER):
        if PROXY_MANAGER.getResource() is None:
            root_ctx = default_context()
            profile_fetcher = ProfileFetcher(root_ctx)

            root_ctx.set("profile_fetcher", profile_fetcher)

            # Lock the context down after we've got basic bits installed
            r_factory = recommenders.RecommenderFactory(root_ctx)
            root_ctx.set("recommender_factory", r_factory)
            instance = recommenders.RecommendationManager(root_ctx)
            PROXY_MANAGER.setResource(instance)
        return PROXY_MANAGER.getResource()

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
