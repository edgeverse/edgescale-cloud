# Pull base image.
FROM busybox:glibc

# Add files.
ADD app-orchestration-server  /root/
ADD ca.pem /root/
ADD server.pem /root/
ADD server-key.pem /root/

# Set environment variables.
ENV HOME /root
ENV MQTT 127.0.0.1
ENV dbhost 127.0.0.1
ENV dbuser root 
ENV mqtopic v1
# Define working directory.
WORKDIR /root

EXPOSE 7443

# Define default command.
CMD echo "";\
	echo "=====*********************************==";\
	echo "ENV: DBURL: $DBURL";\
	echo "     MQTT: $MQTT";\
	echo "=====*********************************===";\
	echo "";\
	/root/app-orchestration-server -dbhost $dbhost -dbuser $dbuser -l 0.0.0.0:7443 -s $MQTT -v 4 -kaddr none
