#!/bin/bash -x
#
# this script expects that you have mcli configured with what you provide through env ${storage}
# in the particular example minio's mc client is show-cased
# 

IMAGE=${1}

skopeo copy docker://${1} dir://tmp/image
for layer in $(ls /tmp/image/* | egrep -v '(json|version|signature)' ) ; do
    echo "checking layer ${layer}"
    blob=$(basename ${layer})
    blobdir=${blob:0:2}
    mcli stat ${storage}/quay-registry/datastorage/registry/sha256/${blobdir}/${blob} || \
        mcli cp ${layer} ${storage}/quay-registry/datastorage/registry/sha256/${blobdir}/${blob}
done
