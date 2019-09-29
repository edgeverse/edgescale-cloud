// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"github.com/eclipse/paho.mqtt.golang"
	"log"
	"time"
)

var mqttClient mqtt.Client

func MqttClient() mqtt.Client {
	deviceID := "system-mft-" + getRandom(4)
	opts := &mqtt.ClientOptions{
		ClientID:       deviceID,
		PingTimeout:    time.Second * 30,
		ConnectTimeout: time.Second * 30,
		AutoReconnect:  true,
		KeepAlive:      60,
	}

	opts.AddBroker(esconf.MQTT)
	client := mqtt.NewClient(opts)
	if token := client.Connect(); token.Wait() && token.Error() != nil {
		log.Println("Connect error: ", token.Error())
	}
	return client
}
