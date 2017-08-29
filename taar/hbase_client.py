import contextlib
import json
import boto3
import logging
from happybase import Connection


logger = logging.getLogger(__name__)


class HBaseClient:
    _hostname = None

    def __init__(self, hbase_hostname=None, table_name='addon_recommender_view'):
        self.tablename = table_name
        self.column_family = b'cf'
        self.column = b'cf:payload'
        if hbase_hostname is None:
            try:
                self.hbase_hostname = self._get_hbase_hostname()
            except Exception:
                logger.exception("Failed to get HBase hostname")
                raise
        else:
            self.hbase_hostname = hbase_hostname

    def _get_hbase_hostname(self):
        client = boto3.client('ec2')
        reservations = client.describe_instances(Filters=[
            {'Name': 'tag:Name', 'Values': ['telemetry-hbase']},
            {
                'Name': 'tag:aws:elasticmapreduce:instance-group-role',
                'Values': ['MASTER']
            }
        ])["Reservations"]

        if len(reservations) == 0:
            raise Exception("HBase master not found!")

        if len(reservations) > 1:
            raise Exception("Multiple HBase masters found!")

        return reservations[0]["Instances"][0]["NetworkInterfaces"][0]["PrivateIpAddress"]

    def get_client_profile(self, client_id):
        """Retrieve the latest row for the given client in HBase

        Only the last known version of the info is retrieved"""
        try:
            with contextlib.closing(Connection(self.hbase_hostname)) as connection:
                table = connection.table(self.tablename)
                client_row = table.row(client_id, columns=[self.column_family])
                if client_row:
                    return json.loads(client_row[self.column].decode("utf-8"))
        except Exception:
            logger.exception("Connection to HBase failed", extra={"client_id": client_id})

        logger.info("Client information not found", extra={"client_id": client_id})
        return None
