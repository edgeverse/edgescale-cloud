
All:
	go get github.com/aws/aws-lambda-go/lambda
	go get github.com/aws/aws-sdk-go/aws
	go get github.com/awslabs/aws-lambda-go-api-proxy/gin
	go get github.com/x-pkg/requests
	go get github.com/jinzhu/gorm
	go get github.com/lib/pq
	go get github.com/google/uuid 
	go get github.com/eclipse/paho.mqtt.golang 
	cd ./cmd &&go build --tags aws --ldflags="-w -s" -o ../build/lambda_handler

clean:
	rm build/lambda_handler 
