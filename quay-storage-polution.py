#!/opt/app-root/bin/python3

import psycopg
import boto3, botocore
from botocore.client import Config
import os, sys

S3CONFIG = Config(connect_timeout=int(os.environ.get('BOTO3_TIMEOUT', 30)),
                  read_timeout=int(os.environ.get('BOTO3_TIMEOUT', 30)),
                  signature_version=os.environ.get('BOTO3_SIGNATURE', 's3v4'))

BUCKET = os.environ.get('BUCKET', '')
REGPATH = os.environ.get('REGPATH', 'datastorage/registry/sha256')
POSTGRESURI = os.environ.get('POSTGRESURI', False)
try:
    S3 = boto3.client('s3',
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                endpoint_url=os.environ.get('ENDPOINT'),
                config=S3CONFIG,
                verify=bool(os.environ.get('SSL_VERIFY', True)))
except Exception as e:
    print(str(e))
    sys.exit(1)

def check_object_in_db(cur, key):
    cur.execute(f"SELECT uuid, content_checksum FROM imagestorage WHERE content_checksum = 'sha256:{key}' LIMIT 1")
    if cur.fetchone() == None:    return False
    return True
    
paginator = S3.get_paginator('list_objects_v2')
pages = paginator.paginate(Bucket=BUCKET, Prefix=REGPATH)
with psycopg.connect(POSTGRESURI) as dbc:
    with dbc.cursor() as cur:
        for objects in pages:
            for info in objects.get('Contents', []):
                #print(f"checking {info.get('Key')}")
                if not check_object_in_db(cur, os.path.basename(info.get('Key'))):
                    print(f"poluting content {info.get('Key')} found in Storage but not in DB")   
