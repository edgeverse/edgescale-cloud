// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"bytes"
	"fmt"
	"github.com/minio/minio-go"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strings"
)

func upload(endpoint string, bucketName string, objectName string, contextType string, filePath string) {
	accessKeyID := "CSSFSisdfEIKNC"
	secretAccessKey := "isdEDegDFfsdfSDjsdlsdfDAO+k"
	useSSL := false
	location := "us-east-1"
	minioClient, err := minio.New(endpoint, accessKeyID, secretAccessKey, useSSL)
	if err != nil {
		log.Fatalln(err)
	}
	buckets, err := minioClient.ListBuckets()
	if err != nil {
		fmt.Println(err)
		return
	}
	for _, bucket := range buckets {
		fmt.Println(bucket)
	}
	err = minioClient.MakeBucket(bucketName, location)
	if err != nil {
		exists, err := minioClient.BucketExists(bucketName)
		if err == nil && exists {
			log.Printf("we already own %s\n", bucketName)
		} else {
			log.Fatalln(err)
		}
	} else {
		log.Printf("Successfully created %s\n,", bucketName)
	}

	contentType := "application/" + contextType
	log.Printf(contentType)
	n, err := minioClient.FPutObject(bucketName, objectName, filePath, minio.PutObjectOptions{ContentType: contentType})
	if err != nil {
		log.Fatal(err)
	}

	os.Remove(filePath)
	log.Printf("Successfully upload %s of size %d\n", objectName, n)
}

func download(rw http.ResponseWriter, endpoint string, bucketName string, username string, objectname string) {
	accessKeyID := "CSSFSisdfEIKNC"
	secretAccessKey := "isdEDegDFfsdfSDjsdlsdfDAO+k"
	useSSL := false
	minioClient, err := minio.New(endpoint, accessKeyID, secretAccessKey, useSSL)
	if err != nil {
		log.Fatalln(err)
	}
	objname := fmt.Sprintf("%slog.txt/%s", username, strings.Split(objectname, "/")[1])
	fmt.Println(bucketName, objname)

	err = minioClient.FGetObject(bucketName, objname, "/tmp/temp.txt", minio.GetObjectOptions{})
	if err != nil {
		fmt.Println(err)
	}
	b, _ := ioutil.ReadFile("/tmp/temp.txt")
	str := string(b)
	rw.Write([]byte(str))
	os.Remove("/tmp/temp.txt")
	fmt.Println("GET Done!")
}

func handler(rw http.ResponseWriter, req *http.Request) {

	var objectName string
	var bucketName string
	var contextType string

	rw.Header().Set("Access-Control-Allow-Origin", "*")
	rw.Header().Set("Access-Control-Allow-Methods", "PUT, GET")
	rw.Header().Set("Access-Control-Allow-Headers", "content-type, dcca_token")

	endpoint := fmt.Sprintf("%s:9000", os.Getenv("hostIp"))
	print(endpoint)
	fmt.Println(endpoint)
	query := req.URL.Query()
	fmt.Println(query)
	rootName := "public-bucket"
	bucketName = query.Get("username")
	objectName = bucketName + "/" + query.Get("objectname")
	contextType = query.Get("type")
	tmpFile := "/tmp/" + query.Get("objectname")
	method := req.Header.Get("Access-Control-Request-Method")
	log.Printf(method)

	var stringBuilder bytes.Buffer
	stringBuilder.WriteString(fmt.Sprintf("http://%s/", endpoint))
	stringBuilder.WriteString(rootName)
	stringBuilder.WriteString("/")
	stringBuilder.WriteString(objectName)
	urls := []byte(stringBuilder.Bytes())
	err_username := []byte("Failed to upload, the usernema is NULL")
	err_objectname := []byte("Failed to upload, the objectname is NULL")
	fmt.Println(req)
	if req.Method == "PUT" {
		log.Printf("Put start\n")
		data, _ := ioutil.ReadAll(req.Body)
		f, _ := os.OpenFile(tmpFile, os.O_CREATE|os.O_WRONLY, 0666)
		defer f.Close()
		f.WriteString(string(data))
		req.Body.Close()
		f.Close()
		host := req.Host
		log.Printf(host)
		log.Printf(bucketName)
		fmt.Println(objectName)
		if bucketName != "" {
			if objectName != "" {
				upload(endpoint, rootName, objectName, contextType, tmpFile)
				rw.Write(urls)
			} else {
				rw.Write(err_objectname)
			}
		} else {
			rw.Write(err_username)
		}

		log.Printf("Put end\n")
	} else if req.Method == "GET" && contextType != "text" {
		log.Printf("Get start\n")
		if bucketName != "" {
			if objectName != "" {
				//	download(bucketName, objectName)
				rw.Write(urls)
			} else {
				rw.Write(err_objectname)
			}
		} else {
			rw.Write(err_username)
		}

		log.Printf("Get end\n")
	} else {
		if bucketName != "" {
			if objectName != "" {
				download(rw, endpoint, rootName, bucketName, objectName)
			}
		} else {
			rw.Write(err_username)
		}
	}
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/signer", handler)
	http.ListenAndServeTLS("0.0.0.0:10086", "/root/edgescale.crt", "/root/edgescale.key", mux)
}
