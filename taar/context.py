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
from srgutil.context import Context


def default_context():
    ctx = Context()
    from taar.recommenders import CollaborativeRecommender
    from taar.recommenders import SimilarityRecommender
    from taar.recommenders import LocaleRecommender
    from taar.cache import Clock
    from taar.cache import JSONCache

    # Note that the EnsembleRecommender is *not* in this map as it
    # needs to ensure that the recommender_map key is installed in the
    # context
    ctx['recommender_factory_map'] = {'collaborative': lambda: CollaborativeRecommender(ctx.child()),
                                      'similarity': lambda: SimilarityRecommender(ctx.child()),
                                      'locale': lambda: LocaleRecommender(ctx.child())}

    ctx['utils'] = utils
    ctx['clock'] = Clock()
    ctx['cache'] = JSONCache(ctx)
    return ctx
