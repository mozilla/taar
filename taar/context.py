"""
A Context is a customizable namespace.

It works like a regular dictionary, but allows you to set a delegate
explicitly to do attribute lookups.

The primary benefit is that the context has a .child() method which
lets you 'lock' a dictionary and clobber the namespace without
affecting parent contexts.

In practice this makes testing easier and allows us to specialize
configuration information as we pass the context through an object
chain.
"""

from taar.recommenders import utils


class Context:
    def __init__(self, delegate=None):
        if delegate is None:
            delegate = {}

        self._local_dict = {}
        self._delegate = delegate

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def __getitem__(self, key):
        # This is a little tricky, we want to lookup items in our
        # local namespace before we hit the delegate
        try:
            result = self._local_dict[key]
        except KeyError:
            result = self._delegate[key]
        return result

    def get(self, key, default):
        try:
            result = self[key]
        except KeyError:
            result = default
        return result

    def __setitem__(self, key, value):
        self._local_dict[key] = value

    def __delitem__(self, key):
        del self._local_dict[key]

    def wrap(self, ctx):
        ctx_child = ctx.child()
        this_child = self.child()
        this_child._delegate = ctx_child
        return this_child

    def child(self):
        """ In general, you should call this immediately in any
        constructor that receives a context """

        return Context(self)


def default_context():
    ctx = Context()
    from taar.recommenders import LegacyRecommender
    from taar.recommenders import CollaborativeRecommender
    from taar.recommenders import SimilarityRecommender
    from taar.recommenders import LocaleRecommender
    from taar.cache import Clock
    from taar.cache import JSONCache

    # Note that the EnsembleRecommender is *not* in this map as it
    # needs to ensure that the recommender_map key is installed in the
    # context
    ctx['recommender_factory_map'] = {'legacy': lambda: LegacyRecommender(ctx.child()),
                                      'collaborative': lambda: CollaborativeRecommender(ctx.child()),
                                      'similarity': lambda: SimilarityRecommender(ctx.child()),
                                      'locale': lambda: LocaleRecommender(ctx.child())}

    ctx['utils'] = utils
    ctx['clock'] = Clock()
    ctx['cache'] = JSONCache(ctx)
    return ctx
