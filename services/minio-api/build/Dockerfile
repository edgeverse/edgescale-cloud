#import base images
FROM busybox:glibc
COPY minio_transfer_server /root/
COPY edgescale.key /root/
COPY edgescale.crt /root/
ENV HOME /root
WORKDIR /root
ENV hostIp 127.0.0.1
CMD ["/root/minio_transfer_server"]

