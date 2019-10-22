// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	minio "github.com/minio/minio-go"
)

func checkErr(err error) {
	if err != nil {
		log.Println(err)
	}
}

// upload file function based on Minio api
func upload(minioClient *minio.Client, bucketName, objectName, contextType, filePath string) {
	location := "us-east-1"

	if exists, _ := minioClient.BucketExists(bucketName); exists {
		log.Printf("we already own %s\n", bucketName)
	} else {
		if err := minioClient.MakeBucket(bucketName, location); err != nil {
			checkErr(err)
		}
	}
	contentType := "application/" + contextType
	fileSize, err := minioClient.FPutObject(bucketName, objectName, filePath, minio.PutObjectOptions{ContentType: contentType})
	checkErr(err)
	os.Remove(filePath)
	log.Printf("Successfully upload %s of size %d\n", objectName, fileSize)
}

// download file function based on Minio api.
func download(rw http.ResponseWriter, minioClient *minio.Client, bucketName, username, objectname string) {
	objname := fmt.Sprintf("%slog.txt/%s", username, strings.Split(objectname, "/")[1])
	err := minioClient.FGetObject(bucketName, objname, "/tmp/tep.txt", minio.GetObjectOptions{})
	checkErr(err)
	data, _ := ioutil.ReadFile("/tmp/temp.txt")
	rw.Write([]byte(string(data)))
	os.Remove("/tmp/temp.txt")
}

func handler(rw http.ResponseWriter, req *http.Request) {
	defer req.Body.Close()

	rw.Header().Set("Access-Control-Allow-Origin", "*")
	rw.Header().Set("Access-Control-Allow-Methods", "PUT, GET")
	rw.Header().Set("Access-Control-Allow-Headers", "content-type, dcca_token")

	endpoint := fmt.Sprintf("%s:9000", os.Getenv("hostIp"))
	accessKeyID := os.Getenv("accessKeyID")
	secretAccessKey := os.Getenv("secretAccessKey")
	query := req.URL.Query()
	rootName := "public-bucket"
	bucketName := query.Get("username")
	objectName := bucketName + "/" + query.Get("objectname")
	contextType := query.Get("type")
	tmpFile := "/tmp/" + query.Get("objectname")
	useSSL := false
	minioClient, err := minio.New(endpoint, accessKeyID, secretAccessKey, useSSL)
	checkErr(err)
	urls := []byte(fmt.Sprintf("http://%s/%s/%s", endpoint, rootName, objectName))
	err_username := []byte("Failed to upload, the username is nil")
	err_objectname := []byte("Failed to upload, the objectname is nil")
	if bucketName == "" {
		rw.Write(err_username)
		return
	}
	if objectName == "" {
		rw.Write(err_objectname)
		return
	}
	switch req.Method {
	case "PUT":
		f, _ := os.OpenFile(tmpFile, os.O_CREATE|os.O_WRONLY, 0666)
		defer f.Close()
		_, err := io.Copy(f, req.Body)
		checkErr(err)
		upload(minioClient, rootName, objectName, contextType, tmpFile)
		rw.Write(urls)
		log.Printf("Upload file complate!\n")
	case "GET":
		rw.Write(urls)
		log.Printf("Get information complate!\n")
	default:
		download(rw, minioClient, rootName, bucketName, objectName)
	}
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/signer", handler)
	s := &http.Server{
		Addr:           ":10086",
		Handler:        mux,
		ReadTimeout:    160 * time.Second,
		WriteTimeout:   1600 * time.Second,
		MaxHeaderBytes: 1 << 20,
	}
	s.ListenAndServeTLS("/root/edgescale.crt", "/root/edgescale.key")
}
