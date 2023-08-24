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
MAXDBTHREADS = int(os.environ.get('MAXDBTHREADS', 5))
blobs_finished = False
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
            logger.debug(f"{self._parent.resolve_image_namefrom_blob(record[0])[0]} missing blob {REGPATH}/{bdir}/{blob}")
            return False
        return True

class DBcheck(object):
    def __init__(self, conn=None,):
        self._conn = conn
        self._cur = conn.cursor()
        self._s3  = S3check(bucket=BUCKET, s3config=S3CONFIG, parent=self)
    def start(self):
        global Images, Blobs, blobs_finished
        while not all([Blobs.empty(),
                       blobs_finished]):
            record = Blobs.get(timeout=1)
            logger.debug(f"checking {record[0]} from DB")
            if not self._s3.check_blob_on_storage(record):
                Images.put(self.resolve_image_namefrom_blob(record[0]))
            Blobs.task_done()
    def resolve_image_namefrom_blob(self, uuid):
        try:
            #self._cur.execute(f"""
            #SELECT public.user.username, repository.name AS name, tag.name AS tag FROM imagestorage
            #LEFT JOIN public.manifestblob ON imagestorage.id = manifestblob.blob_id
            #LEFT JOIN public.repository ON manifestblob.repository_id = repository.id
			#LEFT JOIN public.user ON public.user.id  = repository.namespace_user_id
            #LEFT JOIN public.tag ON manifestblob.id = tag.manifest_id
            #WHERE imagestorage.uuid = '{uuid}'
            #""")
            self._cur.execute(f"""
            SELECT public.user.username AS username, repository.name, tag.name AS tag FROM imagestorage 
            LEFT JOIN manifestblob ON imagestorage.id = manifestblob.blob_id 
            LEFT JOIN repository ON manifestblob.repository_id = repository.id 
            LEFT JOIN tag ON repository.id = tag.repository_id 
            LEFT JOIN public.user ON repository.namespace_user_id = public.user.id 
            WHERE imagestorage.uuid = '{uuid}';
            """)
            return self._cur.fetchone()
        except Exception as reserr:
            logger.error(f"resolving blob uuid to image failed {reserr}")
        return uuid

threads = []
dbthreads = []
pgpool = psycopg2.pool.ThreadedConnectionPool(1, MAXTHREADS+MAXDBTHREADS+1, POSTGRESURI)

def fetch_db_items(dbc, offset, limit):
    global Blobs, pgpool, blobs_finished
    #with pgpool.getconn() as dbc:
    if True:
        with dbc.cursor() as cur:
            cur.execute("SELECT count(uuid) FROM imagestorage")
            total = cur.fetchone()[0]
            logger.info(f"Found {total} blobs in DB, doing offset {offset} limit {limit}")
            cur.execute(f"SELECT uuid, content_checksum FROM imagestorage OFFSET {offset} LIMIT {limit}")
            for record in cur:
                logger.debug(f"adding record {record}")
                Blobs.put(record)
        #blobs_finished = True

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-d', '--debug', action='store_true', default=False)
    options, remainings = parser.parse_args()
    
    if options.debug:   logger.setLevel(logging.DEBUG)
    
    with pgpool.getconn() as dbc:
        with dbc.cursor() as cur:
            cur.execute("SELECT count(uuid) FROM imagestorage")
            total = cur.fetchone()[0]
    with ThreadPoolExecutor(max_workers=MAXTHREADS+MAXDBTHREADS) as tpe:
        limit = total / MAXDBTHREADS
        offset = 0
        with pgpool.getconn() as dbc:
            for x in range(0, MAXDBTHREADS):
                logger.debug(f'starting DBThread {x}')
                dbthreads.append(tpe.submit(fetch_db_items, dbc, round(offset), round(limit)))    
                offset += limit+1
    
        while len(list(filter(lambda x: x.running(), dbthreads))) > 0:
            logger.info(f"{len(list(filter(lambda x: x.running(), dbthreads)))} DB Threads running. {Blobs.qsize()} objects to check")
            sleep(1)
    
        wait(dbthreads)
        print(f"starting on {Blobs.qsize()} objects to check")
        #sys.exit(1)
        with pgpool.getconn() as dbc:
            for x in range(0, MAXTHREADS):
                logger.debug(f'starting Thread {x}')
                threads.append(tpe.submit(DBcheck(conn=dbc).start)) # pgpool.getconn()).start))
    
        while not len(list(filter(lambda x: x.running(), threads))) < 1:
            logger.debug(f"{len(list(filter(lambda x: x.running(), dbthreads)))} DB Threads running. {len(list(filter(lambda x: x.running(), threads)))} Threads running. {Blobs.qsize()} objects to check")
            sleep(5)
    seen = set([])
    while not Images.empty():
        blob = Images.get()
        if blob == (None, None, None):    continue
        if blob in seen:    continue
        logger.info(f"Missing Blob {'/'.join(blob[:2])}:{blob[-1]} in Backend")
        seen.add(blob)
        Images.task_done()
    wait(threads)
