#!/opt/app-root/bin/python3

import psycopg2
from psycopg2 import pool
import boto3, botocore
from botocore.client import Config
from concurrent.futures import ThreadPoolExecutor, wait
from queue import Queue
import os, sys
from time import sleep
import logging
import optparse

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

S3CONFIG = Config(connect_timeout=int(os.environ.get('BOTO3_TIMEOUT', 30)),
                  read_timeout=int(os.environ.get('BOTO3_TIMEOUT', 30)),
                  signature_version=os.environ.get('BOTO3_SIGNATURE', 's3v4'))

BUCKET = os.environ.get('BUCKET', '')
REGPATH = os.environ.get('REGPATH', 'datastorage/registry/sha256')
POSTGRESURI = os.environ.get('POSTGRESURI', False)
DELETE = bool(os.environ.get('DELETE_I_KNOW_WHAT_I_AM_DOING', False))
MAXTHREADS = int(os.environ.get('MAXTHREADS', 10))

polution = Queue()
poluted = Queue()
polution_empty = False
threads = []
total = 0

pgpool = psycopg2.pool.ThreadedConnectionPool(1, MAXTHREADS+1, POSTGRESURI)

class PGConnection(object):
    def __init__(self):
        global polution, polution_empty, pgpool
        conn = pgpool.getconn()
        cur = conn.cursor()
        while not all([polution.empty(), polution_empty]):
            blob = polution.get(timeout=1)
            blobn = os.path.basename(blob)
            logger.debug(f'checking Blob {blob}')
            if not self.check_object_in_db(blobn, cur):
                logger.debug('QuayBlob missing')
                poluted.put(blob)
            polution.task_done()
            logger.debug(f'task_done iterating')
    def check_object_in_db(self, blob, cur):
        logger.debug(f"checking sha256:{blob}")
        cur.execute(f"SELECT uuid, content_checksum FROM imagestorage WHERE content_checksum = 'sha256:{blob}' LIMIT 1")
        if cur.fetchone() == None:    
            logger.info(f"missed {blob} in DB")
            return False
        logger.debug(f"found {blob} in DB")
        return True

def s3thread():
    global polution, polution_empty, threads, total
    try:
        S3 = boto3.client('s3',
                    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                    endpoint_url=os.environ.get('ENDPOINT'),
                    config=S3CONFIG,
                    verify=bool(os.environ.get('SSL_VERIFY', True)))
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)
    paginator = S3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET, Prefix=REGPATH)
    for objects in pages:
        for info in objects.get('Contents', []):
            logger.debug(f"adding content {info.get('Key')}")
            polution.put(info.get('Key'))
            total += 1
    polution_empty = True

def s3cleanup(s3, cobj):
    try:
        print(f"cleaning up {cobj}")
        s3.delete_object(Key=cobj, Bucket=BUCKET)
    except Exception as cleanerr:
        print(f"cleanup error for object {cobj} {cleanerr}")

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-d', '--debug', action='store_true', default=False)
    options, remainings = parser.parse_args()
    
    if options.debug:   logger.setLevel(logging.DEBUG)
    
    threads.append(ThreadPoolExecutor().submit(s3thread))    
    for x in range(0, MAXTHREADS):
        threads.append(ThreadPoolExecutor().submit(PGConnection))

    while not polution_empty: sleep(0.1)
    polution.join()
    wait(threads)
    logger.info(f"Processed {total} Found {poluted.qsize()} items")
    if DELETE:
        try:
            s3 = boto3.client('s3',
                        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                        endpoint_url=os.environ.get('ENDPOINT'),
                        config=S3CONFIG,
                        verify=bool(os.environ.get('SSL_VERIFY', True)))
        except Exception as e:
            logger.error(str(e))
            sys.exit(1)
    while not poluted.empty():
        cobj = poluted.get(timeout=1)
        logger.info(f"poluting content {cobj} found in Storage but not in DB")
        if DELETE:
            s3cleanup(s3, cobj)
        poluted.task_done()
