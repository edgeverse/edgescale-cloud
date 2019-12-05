All:
	go get github.com/google/uuid
	go get github.com/jinzhu/gorm
	go get github.com/sirupsen/logrus
	go get github.com/spf13/pflag
	go get github.com/lib/pq
	cd ./cmd && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build --ldflags="-w -s" -o ../build/task_schedular

clean:
	rm -rf build/task_schedular

