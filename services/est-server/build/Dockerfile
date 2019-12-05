from alpine as certs
RUN apk update && apk add ca-certificates

from busybox:glibc 
COPY --from=certs /etc/ssl/certs /etc/ssl/certs

add estserver /bin/estserver

EXPOSE 443
ENTRYPOINT ["/bin/estserver"]

