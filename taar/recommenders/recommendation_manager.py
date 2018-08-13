# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taar.recommenders.ensemble_recommender import EnsembleRecommender
from taar.recommenders.hybrid_recommender import HybridRecommender
from taar.schema import RecommendationManagerQuerySchema
from srgutil.interfaces import IMozLogging

import colander
import logging

from funcsigs import signature as inspect_sig
import funcsigs

from taar.schema import INTERVENTION_A
from taar.schema import INTERVENTION_B
from taar.schema import INTERVENTION_CONTROL

from taar.context import default_context
from srgutil.interfaces import IMozLogging

ctx = default_context()
schema_logger = ctx[IMozLogging].get_logger('taar.schema_validate')

def schema_validate(colandar_schema):
    """
    Compute the function signature and apply a schema validator on the
    function.
    """
    def real_decorator(func):
        func_sig = inspect_sig(func)

        json_args = {}
        json_arg_names = []
        for key in func_sig.parameters.keys():
            json_arg_names.append(key)
            if key == 'self':
                continue

            default_val = func_sig.parameters[key].default
            if default_val is funcsigs._empty:
                json_args[key] = None
            else:
                json_args[key] = default_val

        def wrapper(*w_args, **w_kwargs):

            if json_arg_names[0] == 'self':
                # first arg is 'self', so this is a method.
                # Strip out self when doing argument validation
                for i, argval in enumerate(w_args[1:]):
                    kname = json_arg_names[i + 1]
                    json_args[kname] = argval
            else:
                for i, argval in enumerate(w_args):
                    kname = json_arg_names[i]
                    json_args[kname] = argval

            # Clobber the kwargs into the JSON version of the argument
            # list
            for k, v in w_kwargs.items():
                json_args[k] = v

            schema = RecommendationManagerQuerySchema()
            try:
                schema.deserialize(json_args)
            except colander.Invalid as e:
                msg = "Defaulting to empty results. Error deserializing input arguments: " + str(e.asdict().values())

                # This logger can't use the context logger as the code
                # is running in a method decorator
                schema_logger.warn(msg)
                # Invalid data means TAAR safely returns an empty list
                return []
            return func(*w_args, **w_kwargs)

        return wrapper
    return real_decorator


class RecommenderFactory:
    """
    A RecommenderFactory provides support to create recommenders.

    The existence of a factory enables injection of dependencies into
    the RecommendationManager and eases the implementation of test
    harnesses.
    """
    def __init__(self, ctx):
        self._ctx = ctx
        # This map is set in the default context
        self._recommender_factory_map = self._ctx['recommender_factory_map']

    def get_names(self):
        return self._recommender_factory_map.keys()

    def create(self, recommender_name):
        return self._recommender_factory_map[recommender_name]()


class RecommendationManager:
    """This class determines which of the set of recommendation
    engines will actually be used to generate recommendations."""

    def __init__(self, ctx):
        """Initialize the user profile fetcher and the recommenders.
        """
        self._ctx = ctx
        self.logger = self._ctx[IMozLogging].get_logger('taar')

        assert 'profile_fetcher' in self._ctx

        profile_fetcher = ctx['profile_fetcher']

        self.profile_fetcher = profile_fetcher
        self._recommender_map = {}

        self.logger.info("Initializing recommenders")
        self._recommender_map[INTERVENTION_A] = EnsembleRecommender(self._ctx.child())

        hybrid_ctx = self._ctx.child()
        hybrid_ctx['ensemble_recommender'] = self._recommender_map[INTERVENTION_A]
        self._recommender_map[INTERVENTION_B] = HybridRecommender(hybrid_ctx)

    @schema_validate(RecommendationManagerQuerySchema)
    def recommend(self, client_id, limit, extra_data={}):
        """Return recommendations for the given client.

        The recommendation logic will go through each recommender and
        pick the first one that "can_recommend".

        :param client_id: the client unique id.
        :param limit: the maximum number of recommendations to return.
        :param extra_data: a dictionary with extra client data.
        """
        client_info = self.profile_fetcher.get(client_id)
        if client_info is None:
            self.logger.warn("Defaulting to empty results.  No client info fetched from dynamo.")
            return []

        # Select recommendation output based on extra_data['branch']
        branch_selector = extra_data.get('branch', INTERVENTION_CONTROL)
        method_selector = branch_selector.replace('-', '_')

        method_name = 'recommend_{}'.format(method_selector)

        self.logger.info("Dispatching to method [{}]".format(method_name))
        branch_method = getattr(self, 'recommend_%s' % method_selector)
        return branch_method(client_info, client_id, limit, extra_data)

    def recommend_intervention_a(self, client_info, client_id, limit, extra_data):
        """ Intervention A is the ensemble method """
        self.logger.info("Intervention A recommendation method invoked")
        recommender = self._recommender_map[INTERVENTION_A]
        return recommender.recommend(client_info, limit, extra_data)

    def recommend_intervention_b(self, client_info, client_id, limit, extra_data):
        """ Intervention A is the ensemble method hybridized with a
        curated list of addons """
        self.logger.info("Intervention B recommendation method invoked")
        recommender = self._recommender_map[INTERVENTION_B]
        return recommender.recommend(client_info, limit, extra_data)

    def recommend_control(self, client_info, client_id, limit, extra_data):
        """Run the control recommender - that is nothing"""
        self.logger.info("Control recommendation method invoked")
        return []
