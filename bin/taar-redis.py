#!/usr/bin/env python
from taar.recommenders.cache import TAARCache
from taar.recommenders.redis_cache import TAARCacheRedis
from taar.context import default_context
import click


@click.command()
@click.option("--reset", is_flag=True, help="Reset the redis cache to an empty state")
@click.option("--load", is_flag=True, help="Load data into redis")
@click.option("--info", is_flag=True, help="Display information about the cache state")
def main(reset, load, info):
    """
    Manage the TAAR+TAARLite redis cache.

    This expecte that the following enviroment variables are set:

    REDIS_HOST
    REDIS_PORT
    """
    if not (reset or load or info):
        print("No options were set!")
        return

    ctx = default_context(TAARCacheRedis)
    cache = ctx[TAARCache]

    if reset:
        if cache.reset():
            print("Successfully flushed db0 bookkeeping database.")
        else:
            print("Error while flushign db0 bookkeeping database.")
    if load:
        cache.safe_load_data()
    if info:
        cache.info()


if __name__ == "__main__":
    main()
