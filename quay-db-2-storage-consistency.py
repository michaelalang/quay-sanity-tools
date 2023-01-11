#!/opt/app-root/bin/python3

import psycopg2
from psycopg2 import pool
import boto3, botocore
from botocore.client import Config
import os, sys
from concurrent.futures import ThreadPoolExecutor, wait
import logging
import optparse
from queue import Queue
from time import sleep

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

S3CONFIG = Config(connect_timeout=int(os.environ.get('BOTO3_TIMEOUT', 30)),
                  read_timeout=int(os.environ.get('BOTO3_TIMEOUT', 30)),
                  signature_version=os.environ.get('BOTO3_SIGNATURE', 's3v4'))

BUCKET = os.environ.get('BUCKET', '')
REGPATH = os.environ.get('REGPATH', 'datastorage/registry/sha256')
POSTGRESURI = os.environ.get('POSTGRESURI', False)
MAXTHREADS = int(os.environ.get('MAXTHREADS', 10))
Blobs = Queue()
Images = Queue()

class S3check(object):
    def __init__(self, bucket=None, s3config=None, parent=None):
        self._bucket = bucket
        self._parent = parent
        self._s3 = boto3.client('s3',
                    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                    endpoint_url=os.environ.get('ENDPOINT'),
                    config=s3config,
                    verify=bool(os.environ.get('SSL_VERIFY', True)))
    def check_blob_on_storage(self, record=None):
        bdir = record[-1].split(':')[1][:2]
        blob = record[-1].split(':')[1]
        try:
            logger.debug(f"calling S3 stat on {REGPATH}/{bdir}/{blob}")
            self._s3.head_object(
                    Bucket=self._bucket, Key=f"{REGPATH}/{bdir}/{blob}")
        except botocore.exceptions.ClientError:
            logger.error(f"{self._parent.resolve_image_namefrom_blob(record[0])[0]} missing blob {REGPATH}/{bdir}/{blob}")
            return False
        return True

class DBcheck(object):
    def __init__(self, conn=None,):
        self._conn = conn
        self._cur = conn.cursor()
        self._s3  = S3check(bucket=BUCKET, s3config=S3CONFIG, parent=self)
    def start(self):
        global Images, Blobs
        while not Blobs.empty():
            record = Blobs.get(timeout=1)
            logger.debug(f"checking {record[0]} from DB")
            if not self._s3.check_blob_on_storage(record):
                Images.put(self.resolve_image_namefrom_blob(record[0]))
    def resolve_image_namefrom_blob(self, uuid):
        self._cur.execute(f"""
        SELECT repository.name FROM imagestorage 
        LEFT JOIN manifestblob ON imagestorage.id = manifestblob.blob_id
        LEFT JOIN repository ON manifestblob.repository_id = repository.id
        WHERE imagestorage.uuid = '{uuid}'
        """)
        return self._cur.fetchone()

threads = []
pgpool = psycopg2.pool.ThreadedConnectionPool(1, MAXTHREADS+1, POSTGRESURI)

def fetch_db_items():
    global Blobs, pgpool
    with pgpool.getconn() as dbc:
        with dbc.cursor() as cur:
            cur.execute("SELECT count(uuid) FROM imagestorage")
            total = cur.fetchone()[0]
            logger.info(f"Found {total} blobs in DB")
            cur.execute("SELECT uuid, image_size, content_checksum FROM imagestorage")
            for record in cur:
                Blobs.put(record)

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-d', '--debug', action='store_true', default=False)
    options, remainings = parser.parse_args()
    
    if options.debug:   logger.setLevel(logging.DEBUG)
    
    threads.append(ThreadPoolExecutor().submit(fetch_db_items))    
    for x in range(0, MAXTHREADS):
        threads.append(ThreadPoolExecutor().submit(DBcheck(conn=pgpool.getconn()).start))

    wait(threads)
