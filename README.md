# Quay sanity check tools

these are inofficial tools to verify consistency between Quay DB content and Quay S3 backend storage. Even though they do not modify any content neither Quay or S3 they are still **unsupported**.

## usage 

* required Environment variables
    * POSTGRESURI='postgresql://`<user>`:`<password>`@`<server>`/`<dbname>`'
    * AWS_ACCESS_KEY_ID=
    * AWS_SECRET_ACCESS_KEY=
    * ENDPOINT=
    * BUCKET=
    * MAXTHREADS=

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
$ export MAXTHREADS=50

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
$ export MAXTHREADS=50

$ podman run -ti --rm -e POSTGRESURI=${POSTGRESURI} \
   -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
   -e ENDPOINT=${ENDPOINT} -e BUCKET=${BUCKET} quay.io/rhn_support_milang/quay-sanity:latest quay-storage-polution.py

poluting content datastorage/registry/sha256/1e/1e0273b07419ce4d6c6fb1b393c060a77c6282faebfa9605b729a5d876c44ce0 found in Storage but not in DB
poluting content datastorage/registry/sha256/5c/5cb78a5fe6f8509bf805869172b1fa9ac169f1e2fa6cc39fa1fb8f04aebcb69b found in Storage but not in DB
poluting content datastorage/registry/sha256/5f/5f4f74b06d89e2ae231968c592958b8d38d27911db49c7584fb6a0ba8991485b found in Storage but not in DB
... [output omitted] ...
~~~

#### removing poluated blobs from storage

**NOTE** do this at your own risk there's no backup which will get you any data back if you deleted the wrong content

~~~
$ export POSTGRESURI='postgresql://admin:admin@localhost/quay'
$ export AWS_ACCESS_KEY_ID=test
$ export AWS_SECRET_ACCESS_KEY=test
$ export ENDPOINT=https://localhost
$ export BUCKET=quay-registry
$ export MAXTHREADS=50

$ podman run -ti --rm -e DELETE_I_KNOW_WHAT_I_AM_DOING=true \
   -e POSTGRESURI=${POSTGRESURI} \
   -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
   -e ENDPOINT=${ENDPOINT} -e BUCKET=${BUCKET} quay.io/rhn_support_milang/quay-sanity:latest quay-storage-polution.py

missed 06038631a24a25348b51d1bfc7d0a0ee555552a8998f8328f9b657d02dd4c64c in DB
missed 1041e80416766a3be14610bcf1b1d9181ea2996dee351a9a2d10e8d370d43dea in DB
missed 14d208dae3be918075fe606e3da760d858da0d40695c0b23e2eaa5bd2f2e481e in DB
missed 262268b65bd5f33784d6a61514964887bc18bc00c60c588bc62bfae7edca46f1 in DB
missed 44115d860fcecaa250b811cc4120d7ba18a2250bada1fe15199de53cefde7fc7 in DB
missed 8710c877fd984499d57127a0316a7a215fb8456a088484aede07c153caef2ca4 in DB
missed 8900b4b4d0c77a3fc7ddc506013ace21f14ec3a4585b4ba944c68e29eec46dfa in DB
missed 8bb7d40847c4846073faba8bd1c62563a43292819c84a92f4c6379d56e688daa in DB
missed c0d6ce90ebd382f29583f3804c176c827adf1aef768c8a84ba2e7576e0f412ec in DB
missed cac2a79d3d6665bca5be59abd9cf09e6cd2e630a8de45dde684c116d63ed9aee in DB
Processed 966 Found 10 items
poluting content datastorage/registry/sha256/06/06038631a24a25348b51d1bfc7d0a0ee555552a8998f8328f9b657d02dd4c64c found in Storage but not in DB
cleaning up datastorage/registry/sha256/06/06038631a24a25348b51d1bfc7d0a0ee555552a8998f8328f9b657d02dd4c64c
poluting content datastorage/registry/sha256/10/1041e80416766a3be14610bcf1b1d9181ea2996dee351a9a2d10e8d370d43dea found in Storage but not in DB
cleaning up datastorage/registry/sha256/10/1041e80416766a3be14610bcf1b1d9181ea2996dee351a9a2d10e8d370d43dea
poluting content datastorage/registry/sha256/14/14d208dae3be918075fe606e3da760d858da0d40695c0b23e2eaa5bd2f2e481e found in Storage but not in DB
cleaning up datastorage/registry/sha256/14/14d208dae3be918075fe606e3da760d858da0d40695c0b23e2eaa5bd2f2e481e
poluting content datastorage/registry/sha256/26/262268b65bd5f33784d6a61514964887bc18bc00c60c588bc62bfae7edca46f1 found in Storage but not in DB
cleaning up datastorage/registry/sha256/26/262268b65bd5f33784d6a61514964887bc18bc00c60c588bc62bfae7edca46f1
poluting content datastorage/registry/sha256/44/44115d860fcecaa250b811cc4120d7ba18a2250bada1fe15199de53cefde7fc7 found in Storage but not in DB
cleaning up datastorage/registry/sha256/44/44115d860fcecaa250b811cc4120d7ba18a2250bada1fe15199de53cefde7fc7
poluting content datastorage/registry/sha256/87/8710c877fd984499d57127a0316a7a215fb8456a088484aede07c153caef2ca4 found in Storage but not in DB
cleaning up datastorage/registry/sha256/87/8710c877fd984499d57127a0316a7a215fb8456a088484aede07c153caef2ca4
poluting content datastorage/registry/sha256/89/8900b4b4d0c77a3fc7ddc506013ace21f14ec3a4585b4ba944c68e29eec46dfa found in Storage but not in DB
cleaning up datastorage/registry/sha256/89/8900b4b4d0c77a3fc7ddc506013ace21f14ec3a4585b4ba944c68e29eec46dfa
poluting content datastorage/registry/sha256/8b/8bb7d40847c4846073faba8bd1c62563a43292819c84a92f4c6379d56e688daa found in Storage but not in DB
cleaning up datastorage/registry/sha256/8b/8bb7d40847c4846073faba8bd1c62563a43292819c84a92f4c6379d56e688daa
poluting content datastorage/registry/sha256/c0/c0d6ce90ebd382f29583f3804c176c827adf1aef768c8a84ba2e7576e0f412ec found in Storage but not in DB
cleaning up datastorage/registry/sha256/c0/c0d6ce90ebd382f29583f3804c176c827adf1aef768c8a84ba2e7576e0f412ec
poluting content datastorage/registry/sha256/ca/cac2a79d3d6665bca5be59abd9cf09e6cd2e630a8de45dde684c116d63ed9aee found in Storage but not in DB
cleaning up datastorage/registry/sha256/ca/cac2a79d3d6665bca5be59abd9cf09e6cd2e630a8de45dde684c116d63ed9aee
~~~


