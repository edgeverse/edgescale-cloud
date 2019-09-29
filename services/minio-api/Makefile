
All:
	go get github.com/minio/minio-go 
	cp ../../install/kubernetes/resource/sslcert/* ./build 
	cd ./cmd &&go build --ldflags="-w -s" -o ../build/minio_transfer_server
clean:
	rm build/minio_transfer_server
	rm build/*key
	rm build/*crt 
