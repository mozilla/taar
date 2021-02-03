# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from flask import request
import json

import markus
from sentry_sdk import capture_exception

# TAAR specific libraries
from taar.context import default_context
from taar.logs.moz_logging import ContextFilter, Logging
from taar.profile_fetcher import ProfileFetcher
from taar.recommenders.guid_based_recommender import GuidBasedRecommender
from taar.recommenders.recommendation_manager import RecommenderFactory, RecommendationManager
from taar.recommenders.redis_cache import TAARCacheRedis
from taar.recommenders.cache import TAARCache

from taar.settings import (
    TAAR_MAX_RESULTS,
    TAARLITE_MAX_RESULTS,
    STATSD_HOST,
    STATSD_PORT,
    PYTHON_LOG_LEVEL,
    NO_REDIS
)


def acquire_taarlite_singleton(PROXY_MANAGER):
    if PROXY_MANAGER.getTaarLite() is None:
        cache_cls = TAARCache if NO_REDIS else TAARCacheRedis
        ctx = default_context(cache_cls=cache_cls, logger_cls=Logging, log_level=PYTHON_LOG_LEVEL)
        root_ctx = ctx.child()
        instance = GuidBasedRecommender(root_ctx)
        PROXY_MANAGER.setTaarLite(instance)
    return PROXY_MANAGER.getTaarLite()


def acquire_taar_singleton(PROXY_MANAGER):
    if PROXY_MANAGER.getTaarRM() is None:
        cache_cls = TAARCache if NO_REDIS else TAARCacheRedis
        ctx = default_context(cache_cls=cache_cls, logger_cls=Logging, log_level=PYTHON_LOG_LEVEL)

        profile_fetcher = ProfileFetcher(ctx)
        ctx["profile_fetcher"] = profile_fetcher

        # Lock the context down after we've got basic bits installed
        root_ctx = ctx.child()
        r_factory = RecommenderFactory(root_ctx)
        root_ctx["recommender_factory"] = r_factory
        instance = RecommendationManager(root_ctx.child())
        PROXY_MANAGER.setTaarRM(instance)
    return PROXY_MANAGER.getTaarRM()


class ResourceProxy(object):
    def __init__(self):
        self._resource = None
        self._taarlite_resource = None

    def setTaarRM(self, rsrc):
        self._resource = rsrc

    def getTaarRM(self):
        return self._resource

    def setTaarLite(self, rsrc):
        self._taarlite_resource = rsrc

    def getTaarLite(self):
        return self._taarlite_resource


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
            (isinstance(row[0], str))
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

    markus.configure(
        backends=[
            {
                # Log metrics to local instance of statsd
                # server. Use DatadogMetrics client
                "class": "markus.backends.datadog.DatadogMetrics",
                "options": {
                    "statsd_host": STATSD_HOST,
                    "statsd_port": STATSD_PORT,
                    "statsd_namespace": "",
                },
            }
        ]
    )

    @app.route("/taarlite/api/v1/addon_recommendations/<string:guid>/")
    def taarlite_recommendations(guid):
        """Return a list of recommendations provided a telemetry client_id."""
        # Use the module global PROXY_MANAGER
        global PROXY_MANAGER
        taarlite_recommender = acquire_taarlite_singleton(PROXY_MANAGER)

        cdict = {"guid": guid}
        normalization_type = request.args.get("normalize", None)
        if normalization_type is not None:
            cdict["normalize"] = normalization_type

        def set_extra(record):
            record.url = request.path
            record.guid = guid

        with ContextFilter(taarlite_recommender.logger, set_extra):
            recommendations = taarlite_recommender.recommend(
                client_data=cdict, limit=TAARLITE_MAX_RESULTS
            )

        if len(recommendations) != TAARLITE_MAX_RESULTS:
            recommendations = []

        # Strip out weights from TAAR results to maintain compatibility
        # with TAAR 1.0
        jdata = {"results": [x[0] for x in recommendations]}

        response = app.response_class(
            response=json.dumps(jdata), status=200, mimetype="application/json"
        )
        return response

    @app.route(
        "/v1/api/client_has_addon/<hashed_client_id>/<addon_id>/", methods=["GET"],
    )
    def client_has_addon(hashed_client_id, addon_id):
        # Use the module global PROXY_MANAGER
        global PROXY_MANAGER
        recommendation_manager = acquire_taar_singleton(PROXY_MANAGER)
        pf = recommendation_manager._ctx["profile_fetcher"]

        client_meta = pf.get(hashed_client_id)
        if client_meta is None:
            # no valid client metadata was found for the given
            # clientId
            result = {"results": False, "error": "No client found"}
            response = app.response_class(
                response=json.dumps(result), status=200, mimetype="application/json",
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
            capture_exception(e)
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

        recommendation_manager = acquire_taar_singleton(PROXY_MANAGER)

        def set_extra(record):
            record.url = request.path
            if locale:
                record.locale = locale
            if platform:
                record.platform = platform
            record.client_id = client_id
            record.method = request.method

        with ContextFilter(recommendation_manager.logger, set_extra):
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
