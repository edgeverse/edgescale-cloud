// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"encoding/json"
	"fmt"
	"github.com/fatih/structs"
	"github.com/go-redis/redis"
	"github.com/yosssi/gmq/mqtt"
	"github.com/yosssi/gmq/mqtt/client"
	"log"
	"os"
	"strings"
	"time"
)

type Status struct {
	ID        string   `json:"id"`
	Timestamp string   `json:"timestamp"`
	CPUUsage  string   `json:"cpuusage,omitempty"`
	CPUNum    int      `json:"cpunum,omitempty"`
	CPUFreq   int      `json:"cpufreq,omitempty"`
	MemTotal  uint64   `json:"memtotal,omitempty"`
	MemUsage  string   `json:"memusage,omitempty"`
	AppNumber string   `json:"appnumber,omitempty"`
	AppList   []string `json:"applist,omitempty"`
	EsVersion string   `json:"esversion,omitempty"`
	IpAddr    string   `json:"ipaddress,omitempty"`
	DiskFree  string   `json:"diskfree,omitempty"`
	DiskUsed  string   `json:"diskused,omitempty"`
}

func main() {
	PASSWORD := os.Getenv("RedisPassword")
	MqttAddress := os.Getenv("MqttAddress")
	cli := client.New(&client.Options{
		ErrorHandler: func(err error) {
			log.Println(err)
			os.Exit(1)
		},
	})

	defer cli.Terminate()

	err := cli.Connect(&client.ConnectOptions{
		Network:      "tcp",
		Address:      MqttAddress,
		CleanSession: true,
		ClientID:     []byte("iot-system"),
	})
	if err != nil {
		panic(err)
	}
	RedisAddress := os.Getenv("RedisAddress")
	redisClient := createClient(RedisAddress, PASSWORD)
	defer redisClient.Close()
	statusChannel := make(chan Status, 10240)
	topic := "edgescale/cloud/system/status"
	if os.Getenv("mqtopic") == "v1" {
		topic = "edgescale/health/internal/system/status"
	}

	err = cli.Subscribe(&client.SubscribeOptions{
		SubReqs: []*client.SubReq{
			&client.SubReq{
				TopicFilter: []byte(topic),
				QoS:         mqtt.QoS0,
				Handler: func(topicName, message []byte) {
					var m Status
					json.Unmarshal(message, &m)
					log.Println(m.ID, m.Timestamp, m.CPUUsage, m.MemUsage, m.AppNumber)
					//ts := time.Now().Format(time.RFC3339)
					now := time.Now()
					year, mon, day := now.UTC().Date()
					hour, min, sec := now.UTC().Clock()
					m.Timestamp = fmt.Sprintf("%d-%d-%dT%02d:%02d:%02dZ", year, mon, day, hour, min, sec)
					if m.CPUUsage != "" {
						if m.IpAddr != "" {
							go func() {
								statusChannel <- m
							}()
						}
					} else {
						fmt.Println("update status info fiald")
					}
					checkErr(err)
				},
			},
		},
	})
	for i := range statusChannel {
		statusOperation(redisClient, i)
		checkErr(err)
	}
	select {}

}

//creat new redis client
func createClient(host string, password string) *redis.Client {
	client := redis.NewClient(&redis.Options{
		Addr:     host,
		Password: password,
		DB:       0,
		PoolSize: 20,
	})
	_, err := client.Ping().Result()
	if err != nil {
		panic(err)
	}
	return client
}

func sliceToStrMap(elements []string) map[string]string {
	elementMap := make(map[string]string)
	for _, s := range elements {
		elementMap[s] = s
	}
	return elementMap
}

//put device status to redis
func statusOperation(client *redis.Client, status Status) {
	mstatus := structs.Map(status)
	mstatus["AppList"] = strings.Join(mstatus["AppList"].([]string), ",")
	err := client.HMSet(status.ID, mstatus)
	log.Println(err)
	client.Expire(status.ID, 180*time.Second)
}

//func (m *Status) MarshalBinary() ([]byte, error) {
//	return json.Marshal(m)
//}

func checkErr(err error) {
	if err != nil {
		log.Println(err)
	}
}
