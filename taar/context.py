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

# Clobber the Context name to prevent messy name collisions
from srgutil.context import default_context as _default_context
import os
from taar.recommenders.s3config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


def default_context():
    ctx = _default_context()
    from taar.recommenders import CollaborativeRecommender
    from taar.recommenders import SimilarityRecommender
    from taar.recommenders import LocaleRecommender

    # Note that the EnsembleRecommender is *not* in this map as it
    # needs to ensure that the recommender_map key is installed in the
    # context
    ctx.set(
        "recommender_factory_map",
        {
            "collaborative": lambda: CollaborativeRecommender(ctx),
            "similarity": lambda: SimilarityRecommender(ctx),
            "locale": lambda: LocaleRecommender(ctx),
        },
    )

    # You have to stuff the s3config attributes into the context as
    # the context object is passed to worker nodes in spark.

    # Using python-decouple on spark worker nodes won't work as the
    # workers will not be configured the same as the master node.
    ctx.set("AWS_ACCESS_KEY_ID", AWS_ACCESS_KEY_ID)
    ctx.set("AWS_SECRET_ACCESS_KEY", AWS_SECRET_ACCESS_KEY)

    return ctx
