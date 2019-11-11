FROM openfaas/of-watchdog:0.5.3 as watchdog
FROM python:3.7-alpine

COPY --from=watchdog /fwatchdog /usr/bin/fwatchdog
RUN chmod +x /usr/bin/fwatchdog
RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev 
ARG ADDITIONAL_PACKAGE
# Alternatively use ADD https:// (which will not be cached by Docker builder)
RUN apk --no-cache add ${ADDITIONAL_PACKAGE}

# Add non root user
RUN addgroup -S app && adduser app -S -G app
RUN chown app /home/app

USER app

ENV PATH=$PATH:/home/app/.local/bin

WORKDIR /home/app/

COPY index.py           .
USER root
USER app

RUN mkdir -p function
RUN touch ./function/__init__.py
WORKDIR /home/app/function/
COPY function/requirement.txt	.
RUN pip install --user -r requirement.txt

WORKDIR /home/app/

USER root
COPY function   function
RUN chown -R app:app ./
USER app
ENV DB_HOST="postgres-external.openfaas-util"
ENV DB_PASSWORD="edgescale"
ENV VERSION = "v1906"
# Set up of-watchdog for HTTP mode
ENV fprocess="python index.py"
ENV cgi_headers="true"
ENV exec_timeout="25"
ENV read_timeout="25"
ENV mode="http"
ENV upstream_url="http://127.0.0.1:5000"
HEALTHCHECK --interval=5s CMD [ -e /tmp/.lock ] || exit 1

CMD ["fwatchdog"]
