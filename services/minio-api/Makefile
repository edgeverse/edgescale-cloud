
All:
	go get github.com/minio/minio-go 
	cp ../../install/kubernetes/j2_conf/kong/* ./build 
	cd ./cmd &&go build --ldflags="-w -s" -o ../build/minio_transfer_server
clean:
	rm build/minio_transfer_server
	rm build/*key
	rm build/*crt 
