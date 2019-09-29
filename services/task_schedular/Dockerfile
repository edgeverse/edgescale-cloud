FROM python:3.7-alpine

ENV http_proxy=http://wbi\nxf42681:Welcome%402017@92.121.140.44:8080
RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev 
ENV DB_HOST="postgres-external.openfaas-util"
ENV DB_USER="root"
ENV DB_PORT="5432"
ENV DB_DATABASE="edgescale"
ENV DB_PASSWORD="edgescale"

ADD ./  /tmp
WORKDIR /tmp
RUN pip install -r requirements.txt
CMD ["sh","/tmp/run.sh"]

