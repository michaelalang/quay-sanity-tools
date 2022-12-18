# Quay sanity check tools

these are inofficial tools to verify consistency between Quay DB content and Quay S3 backend storage. Even though they do not modify any content neither Quay or S3 they are still **unsupported**.

## usage 

* required Environment variables
    * POSTGRESURI='postgresql://`<user>`:`<password>`@`<server>`/`<dbname>`'
    * AWS_ACCESS_KEY_ID=
    * AWS_SECRET_ACCESS_KEY=
    * ENDPOINT=
    * BUCKET=

running the tools without parameters to get the possible tools to run

~~~
$ podman run -ti quay.io/rhn_support_milang/quay-sanity:latest
please specify quay-db-2-storage-consistency.py or quay-storage-polution.py
~~~

### quay-db-2-storage-consistency.py 

this check iterates over all image layers that are currently in Quay DB. It does a head check on the object in the S3 Storage to verify existence and accessibility.

`NOTE: the tool does only output something if there is something missing`

~~~
$ export POSTGRESURI='postgresql://admin:admin@localhost/quay'
$ export AWS_ACCESS_KEY_ID=test
$ export AWS_SECRET_ACCESS_KEY=test
$ export ENDPOINT=https://localhost
$ export BUCKET=quay-registry

$ podman run -ti --rm -e POSTGRESURI=${POSTGRESURI} \
   -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
   -e ENDPOINT=${ENDPOINT} -e BUCKET=${BUCKET} quay.io/rhn_support_milang/quay-sanity:latest quay-db-2-storage-consistency.py

('ubi8',) missing blob datastorage/registry/sha256/65/6510149c8e6443f28e5a53b6acb0b57165f1b003677d54e1cba821367c0de81a
~~~

### quay-storage-polution.py

this check iterates over all S3 objects in the given Bucket and verifies existence in Quay DB.

`NOTE: the tool does only output something if there is something missing`

~~~
$ export POSTGRESURI='postgresql://admin:admin@localhost/quay'
$ export AWS_ACCESS_KEY_ID=test
$ export AWS_SECRET_ACCESS_KEY=test
$ export ENDPOINT=https://localhost
$ export BUCKET=quay-registry

$ podman run -ti --rm -e POSTGRESURI=${POSTGRESURI} \
   -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
   -e ENDPOINT=${ENDPOINT} -e BUCKET=${BUCKET} quay.io/rhn_support_milang/quay-sanity:latest quay-storage-polution.py

poluting content datastorage/registry/sha256/1e/1e0273b07419ce4d6c6fb1b393c060a77c6282faebfa9605b729a5d876c44ce0 found in Storage but not in DB
poluting content datastorage/registry/sha256/5c/5cb78a5fe6f8509bf805869172b1fa9ac169f1e2fa6cc39fa1fb8f04aebcb69b found in Storage but not in DB
poluting content datastorage/registry/sha256/5f/5f4f74b06d89e2ae231968c592958b8d38d27911db49c7584fb6a0ba8991485b found in Storage but not in DB
... [output omitted] ...
~~~

