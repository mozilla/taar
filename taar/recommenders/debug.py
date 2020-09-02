# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import time


@contextlib.contextmanager
def log_timer_debug(msg, logger):
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        logger.debug(msg + f" Completed in {end_time-start_time} seconds")


@contextlib.contextmanager
def log_timer_info(msg, logger):
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        logger.info(msg + f" Completed in {end_time-start_time} seconds")
