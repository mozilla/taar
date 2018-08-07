import boto3
import json
from srgutil.interfaces import IMozLogging, IClock
import threading


class LazyJSONLoader:
    def __init__(self, ctx, s3_bucket, s3_key, ttl=14400):
        self._ctx = ctx
        self.logger = self._ctx[IMozLogging].get_logger('srgutil')
        self._clock = self._ctx[IClock]

        self._s3_bucket = s3_bucket
        self._s3_key = s3_key
        self._ttl = int(ttl)
        self._expiry_time = 0

        self._key_str = "{}|{}".format(self._s3_bucket, self._s3_key)

        self._cached_copy = None
        msg = "Cache expiry of {} is set to TTL of {} seconds".format(self._key_str, self._ttl)
        self.logger.info(msg)

        self._lock = threading.RLock()

        self.logger.info("{} loader is initialized".format(self._key_str))

    def has_expired(self):
        return self._clock.time() > self._expiry_time

    def get(self):
        """
        Return the JSON defined at the S3 location in the constructor.

        The get method will reload the S3 object after the TTL has
        expired.
        Fetch the JSON object from cache or S3 if necessary
        """
        if not self.has_expired() and self._cached_copy is not None:
            return self._cached_copy, False

        return self._refresh_cache(), True

    def _refresh_cache(self):
        with self._lock:
            # If some requests get stale data while the S3 bucket is
            # being reloaded - it's not the end of the world.
            #
            # Likewise when the TTL expires, it's possible for
            # multiple threads to concurrently lock and update the
            # cache.  Again - not world ending.
            #
            # Immediately update the expiry time as we don't want other
            # threads to wait on the lock while we update the
            # cached_copy
            #
            self._expiry_time = self._clock.time() + self._ttl

            raw_data = None
            raw_bytes = None
            try:
                # We need to force a data reload from S3
                s3 = boto3.resource('s3')
                raw_bytes = (
                    s3
                    .Object(self._s3_bucket, self._s3_key)
                    .get()['Body']
                    .read()
                )
                msg = "Loaded JSON from S3: {}".format(self._key_str)
                self.logger.info(msg)

                raw_data = (
                    raw_bytes.decode('utf-8')
                )

                # It is possible to have corrupted files in S3, so
                # protect against that.
                try:
                    self._cached_copy = json.loads(raw_data)
                except ValueError:
                    # In the event of an error, we want to try to reload
                    # the data so force the expiry to 0, but leave the
                    # existing cached data alone so we can still service
                    # requests.
                    self._expiry_time = 0

                    self.logger.error("Cannot parse JSON resource from S3", extra={
                        "bucket": self._s3_bucket,
                        "key": self._s3_key})

                return self._cached_copy
            except Exception:
                # In the event of an error, we want to try to reload
                # the data so force the expiry to 0, but leave the
                # existing cached data alone so we can still service
                # requests.
                self._expiry_time = 0

                self.logger.exception("Failed to download from S3", extra={
                    "bucket": self._s3_bucket,
                    "key": self._s3_key})
                return self._cached_copy
