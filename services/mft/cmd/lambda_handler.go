// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"fmt"
	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/awslabs/aws-lambda-go-api-proxy/gin"
	"github.com/gin-gonic/gin"
	"github.com/jinzhu/gorm"
	"net/http"
	"time"
)

var db *gorm.DB
var esdb *gorm.DB
var ginLambda *ginadapter.GinLambda

func Handler(req events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	// If no name is provided in the HTTP request body, throw an error
	return ginLambda.Proxy(req)
}

func Cors() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Add("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Add("Access-Control-Allow-Headers", "dcca_token,Content-Type")
		if c.Request.Method == "OPTIONS" {
			c.JSON(http.StatusOK, "Options Request!")
		}
		c.Next()
	}
}

func TestHandler(c *gin.Context) {
	c.JSON(200, gin.H{
		"oid": GetOemID(c),
	})
}

func init() {
	r := gin.Default()
	r.Use(Cors())

	r.GET("/v1/mft", MftListHandler)
	r.POST("/v1/mft", MftCreateHandler)
	r.POST("/v1/mft/devices", MftCreateDeviceHandler)
	r.DELETE("/v1/mft/:id", MftDeleteHandler)
	r.GET("/v1/mft/:id/statistics", MftStatisticsHandler)
	r.GET("/v1/mft/:id", MftStatisticsHandler)
	r.PUT("/v1/mft/:id", MftUpdateHandler)
	r.GET("/v1/mft/:id/devices", MftListDevicesHandler)
	r.GET("/v1/mft/:id/pos", MftConfigDownloadHandler)

	r.POST("/v1/key", RootKeyCreateHandler)
	r.GET("/v1/key", RootKeyListHandler)
	r.GET("/v1/key/:id", RootKeyDetailHandler)
	r.GET("/v1/key/:id/download", RootKeyDownloadHandler)
	r.POST("/v1/key/:id/sign", RootKeySignHandler)
	r.DELETE("/v1/key/:id", RootKeyDeleteHandler)
	r.PUT("/v1/key/:id", RootKeyUpdateHandler)

	r.POST("/v1/fuse", FuseConfigCreateHandler)
	r.GET("/v1/fuse", FuseConfigListHandler)
	r.PUT("/v1/fuse/:id", FuseConfigUpdateHandler)
	r.DELETE("/v1/fuse/:id", FuseConfigDeleteHandler)
	r.GET("/v1/fuse/:id", FuseConfigDetailHandler)

	r.POST("/v1/enroll/challenge", EnrollChallengeHandler)
	r.POST("/v1/enroll/auth", EnrollAuthHandler)
	r.POST("/v1/enroll/token", EnrollETokenHandler)
	r.POST("/v1/enroll/device", DeviceBatchCreateHandle)
	r.DELETE("/v1/enroll/device", DeviceBatchDeleteHandler)
	r.GET("/v1/enroll/device/:id", EnrollStatusGetHandler)
	r.DELETE("/v1/enroll/device/:id", EnrollDestroyCheckHandler)
	r.PATCH("/v1/enroll/device/:id", EnrollStatusPatchHandler)

	r.GET("/v1/est/device", MftCreateDevicePrepHandler)
	r.GET("/v1/devices/certificates", MftCreateDeviceKeyHandler)

	r.GET("/v1/customers/:id/devices", CustomerDeviceListHandler)

	r.GET("/v1/test", TestHandler)
	go r.Run(":8082")

	ginLambda = ginadapter.New(r)
}

func main() {
	var err error
	ESConfInit()
	db, err = gorm.Open("postgres", fmt.Sprintf("host=%s user=%s dbname=%s sslmode=disable password=%s",
		esconf.Mft.DBHost, esconf.Mft.DBUser, esconf.Mft.DBName, esconf.Mft.DBPass))
	if err != nil {
		panic(err)
	}
	db.DB().SetMaxOpenConns(100)
	db.DB().SetConnMaxLifetime(time.Minute * 10)
	db.DB().SetMaxIdleConns(30)
	defer db.Close()

	esdb, err = gorm.Open("postgres", fmt.Sprintf("host=%s user=%s dbname=%s sslmode=disable password=%s",
		esconf.ESDB.DBHost, esconf.ESDB.DBUser, esconf.ESDB.DBName, esconf.ESDB.DBPass))
	if err != nil {
		panic(err)
	}
	esdb.DB().SetMaxOpenConns(100)
	esdb.DB().SetConnMaxLifetime(time.Minute * 10)
	esdb.DB().SetMaxIdleConns(30)
	defer esdb.Close()
	mqttClient = MqttClient()
	db.Exec("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
	db.AutoMigrate(&RootKey{}, &FuseConfig{}, &DeviceModel{}, &Device{}, &Customer{}, &Projects{})

	lambda.Start(Handler)
}
