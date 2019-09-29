#import base images
FROM busybox:glibc

COPY message-handler /root/
ENV HOME /root
ENV MqttAddress="emqtt-external.openfaas-util:1883"
ENV RedisAddress="redis-external.openfaas-util:6379"
ENV RedisPassword="edgescale"
ENV mqtopic="v1"
CMD ["./root/message-handler"]

