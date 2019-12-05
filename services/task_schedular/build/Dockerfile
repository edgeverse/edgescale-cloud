# Pull base image.
FROM busybox:glibc

# Add files.
ADD task_schedular  /root/
ADD server.pem /root/
ADD server-key.pem /root/

# Set environment variables.
ENV HOME /root
ENV dbhost 127.0.0.1
ENV dbuser root 
ENV dbpwd edgescale
ENV apphost "127.0.0.1"
ENV maxpool 20

# Define working directory.
WORKDIR /root

# Define default command.
CMD /root/task_schedular --db_host $dbhost --db_user $dbuser --db_pwd "$dbpwd" --log_level 4 --app_host $apphost --max_pool $maxpool --cert_file server.pem --key_file server-key.pem

