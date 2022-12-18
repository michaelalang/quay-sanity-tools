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

def resolve_image_namefrom_blob(uuid):
    cur.execute(f"""
    SELECT repository.name FROM imagestorage 
    LEFT JOIN manifestblob ON imagestorage.id = manifestblob.blob_id
    LEFT JOIN repository ON manifestblob.repository_id = repository.id
    WHERE imagestorage.uuid = '{uuid}'
    """)
    return cur.fetchone()

def check_blob_on_storage(record):
    bdir = record[-1].split(':')[1][:2]
    blob = record[-1].split(':')[1]
    try:
        pinfo = S3.head_object(
                Bucket=BUCKET, Key=f"{REGPATH}/{bdir}/{blob}")
    except botocore.exceptions.ClientError:
        print(f"{resolve_image_namefrom_blob(record[0])} missing blob {REGPATH}/{bdir}/{blob}")

with psycopg.connect(POSTGRESURI) as dbc:
    with dbc.cursor() as cur:
        cur.execute("SELECT uuid, image_size, content_checksum FROM imagestorage")
        for record in cur:
            check_blob_on_storage(record)
