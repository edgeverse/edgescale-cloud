# Pull base image.
FROM busybox:glibc

# Add files.
ADD  lambda_handler /root/
# Set environment variables.
ENV HOME /root
# Define working directory.
WORKDIR /root

EXPOSE 8082 
# Define default command.
CMD /root/lambda_handler
