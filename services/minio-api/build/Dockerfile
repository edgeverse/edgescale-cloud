#import base images
FROM busybox:glibc
COPY minio_transfer_server /root/
COPY edgescale.key /root/
COPY edgescale.crt /root/
ENV HOME /root
WORKDIR /root
ENV hostIp "minio-external.openfaas-util"
ENV accessKeyID "CSSFSisdfEIKNC"
ENV secretAccessKey "isdEDegDFfsdfSDjsdlsdfDAO+k"
CMD ["/root/minio_transfer_server"]

