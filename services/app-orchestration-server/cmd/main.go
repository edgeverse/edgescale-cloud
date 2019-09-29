// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/sirupsen/logrus"
)

//const loglevl = logrus.InfoLevel

var (
	log         = logrus.New()
	laddress    = flag.String("l", "127.0.0.1:6443", "listen address:port")
	dlevel      = flag.Uint("v", 1, "debug level 0-5, 0:panic, 1:Fatal, 2:Error, 3:Warn, 4:Info 5:debug")
	dynamoEnd   = flag.String("d", "", "dynamodb endpoint Eg: http://127.0.0.1:8000, default null(aws url auto)")
	mqttserver  = flag.String("s", "int.msg.edgescale.org", "mqtt server host address")
	clientid    = flag.String("cid", "A00001AppManagementServer", "mqtt clientid")
	cafile      = flag.String("ca", "ca.pem", "RootCA Cert file")
	certfile    = flag.String("cert", "server.pem", "Https rest api server certification file")
	certkeyfile = flag.String("key", "server-key.pem", "Https rest api server private key file")
	kubeaddr    = flag.String("kaddr", "", "back compatible kube master ipaddress:port(eg: 127.0.0.1:8090), default disable")
	logdir      = flag.String("logdir", os.Getenv("HOME")+"/.edgescale", "edgescale log dir")
	dbhost      = flag.String("dbhost", "127.0.0.1", "edgescale database host")
	dbport      = flag.Int("dbport", 5432, "edgescale database port")
	dbname      = flag.String("dbname", "edgescale", "edgescale database name")
	dbuser      = flag.String("dbuser", "edgescale", "edgescale database user")
	dbpwd       = flag.String("dbpwd", "edgescale", "edgescale database user password")
)

var EdgeCfg EdgeText

func ParseFlags() {
	flag.Parse()

	fmt.Println("=====Input Parameter:======")
	fmt.Println("    debuglevel: ", *dlevel)
	fmt.Println("    http server listen address: ", *laddress)
	fmt.Println("    mqtt server address: ", *mqttserver)
	fmt.Println("    mqtt client id : ", *clientid)
	fmt.Println("    kubeaddr: ", *kubeaddr)
	fmt.Println("    dynamoDB endpoint : ", *dynamoEnd)
	fmt.Println("    edgescale log dir : ", *logdir)
	fmt.Println("==========END==============")
}

func Init() {
	ParseFlags()

	//log level and  format
	//log.Out = os.Stdout
	log.SetLevel(logrus.Level(*dlevel))
	log.Formatter = &logrus.TextFormatter{FullTimestamp: true}

	//Init DB and Memory Cache Interface
	InitDynamoDb()

	var err error
	EdgeCfg, err = ReadConfig(*dbhost, *dbport, *dbname, *dbuser, *dbpwd)
	if err != nil {
		log.Fatalln("ERROR:", "DBGetEdgeConfig", err)
		panic(err)
	}
	if b, err := json.Marshal(EdgeCfg); err == nil {
		log.Info("get config: ", string(b))
	}

	InitDB(*dbhost, *dbuser, *dbpwd, *dbname)
	InitRedisDB(EdgeCfg.Settings.REDISHOST, EdgeCfg.Settings.REDISPORT, EdgeCfg.Settings.REDISPWD, EdgeCfg.Settings.REDISDB)

	InitCache()
	InitStore()
}

func main() {
	Init()
	defer CloseDB()
	defer CloseRedisDB()

	go MqttListen()
	go TaskHandlerLoop()
	KubeListen()

	log.Infoln("Initial Success!")
	StartHTTPServer(*laddress, *cafile, *certfile, *certkeyfile)
}
