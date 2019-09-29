// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	//b64 "encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	_ "io/ioutil"
	"os"
	"regexp"
	"strings"
	"time"

	MQTT "github.com/eclipse/paho.mqtt.golang"
	//"github.com/yosssi/gmq/mqtt"
	//"github.com/yosssi/gmq/mqtt/client"
)

var mqchan chan MqcmdL = make(chan MqcmdL, 50000)
var mqchanlimit chan bool = make(chan bool, 2000)

var mqdbchan chan Mqkubecmd = make(chan Mqkubecmd, 100000)

//var mqdbchanlimit chan bool = make(chan bool, 50)

var mqcli MQTT.Client

func connLostHandler(c MQTT.Client, err error) {
	fmt.Printf("Connection lost, reason: %v\n", err)
	mqcli.Disconnect(1000)
	InitMqtt()
	//panic(err)
}

func InitMqtt() error {

	opts := MQTT.NewClientOptions().AddBroker(fmt.Sprintf("tcp://%s:1883", *mqttserver)).
		SetClientID(*clientid).
		SetCleanSession(false).
		SetConnectionLostHandler(connLostHandler)

	mqcli = MQTT.NewClient(opts)
	token := mqcli.Connect()
	for !token.WaitTimeout(3 * time.Second) {
	}

	log.Infof("Mqtt Connected to: %s:1883", *mqttserver)

	topic := fmt.Sprintf("edgescale/cloud/system/app")
	if os.Getenv("mqtopic") == "v1" {
		topic = "edgescale/kube/devices/app"
	}

	mqcli.Subscribe(topic, 0, func(client MQTT.Client, msg MQTT.Message) {
		MqttCmdHandler([]byte(msg.Topic()), []byte(msg.Payload()))
	})
	/*
		mqcli = client.New(&client.Options{
			ErrorHandler: func(err error) {
				log.Println("MQTT Client ErrorHandler: ", err)
				mqcli.Terminate()
				panic(err)
			},
		})
		topic := fmt.Sprintf("edgescale/kube/devices/app")

		err := mqcli.Connect(&client.ConnectOptions{
			Network:         "tcp",
			Address:         fmt.Sprintf("%s:1883", *mqttserver),
			CleanSession:    false,
			ClientID:        []byte("A00001AppManagementServer"),
			CONNACKTimeout:  10,
			PINGRESPTimeout: 10,
			KeepAlive:       30,
			TLSConfig:       nil,
		})
		if err != nil {
			panic(err)
			return err
		}
		log.Infof("Mqtt Connected to: %s:1883", *mqttserver)

		err = mqcli.Subscribe(&client.SubscribeOptions{
			SubReqs: []*client.SubReq{
				&client.SubReq{
					TopicFilter: []byte(topic),
					QoS:         mqtt.QoS0,
					//QoS:         2,
					Handler: func(topicName, message []byte) {
						MqttCmdHandler(topicName, message)
					},
				},
			},
		})
		if err != nil {
			panic(err)
		}
		return nil
	*/
	log.Info("Success to register Mqtt Handler")
	return nil

}

func MqttCmdHandler(topicName, message []byte) {
	var m Mqkubecmd
	log.Debugln("MqttHandler:", string(topicName), string(message))

	err := json.Unmarshal(message, &m)
	if err != nil {
		log.Errorln("ProcessMQTTcmd:", err)
	}
	switch m.Type {
	//case ACTCREATE:
	case ACTSTATUS:
		_ = MqUpdateAppStatus(m)

	case ACTPUTLOG:
		SaveDockerLog(m.Podname, m.Body)

	case ACTSYNC:
		// Workaround OOM, if podmessage is null, suppose to update but sync.
		if len(m.Podmessage) > 10 {
			log.Debugln("Workaround OOM, Update Message: ", m.Podmessage)
			_ = MqUpdateAppStatus(m)
			return
		}
		err = SyncDeviceapps(m.DeviceId)
		if err != nil {
			log.Errorln("mqhandler", ACTSYNC, err)
		}

	case ACTDELETE:
		_ = MqUpdateAppStatus(m)
	}
}

func AppsToMqtt(app []Application, cmdtype string) MqcmdL {
	//log.Debugln("To http len:", len(app))
	r := make([]Mqkubecmd, len(app))
	for i, v := range app {
		if cmdtype == ACTSYNC && strings.HasPrefix(v.Status, "dele") {
			r[i].Type = ACTDELETE
		} else {
			r[i].Type = cmdtype
		}
		r[i].Podname = v.Appname
		r[i].DeviceId = v.Deviceid
		r[i].Body = v.Cfgfactory
	}
	return MqcmdL{
		Type:  cmdtype,
		Items: r,
	}
}

//send create cmd
func MQcreatApp(app Application) error {
	log.Debugln("MQcreateApp invoked")
	if ok, _ := IsDeviceReady(app.Deviceid); !ok {
		return nil
	}
	if len(app.Cfgfactory) < 20 {
		log.Debugf("valid app:", app.Appname)
		return errors.New("valid app cfg")
	}
	go SendMqAction(append([]Application{}, app), ACTCREATE)
	return nil
}

//send delete cmd
func MQdeleteApp(app Application) error {
	log.Debugln("MQdeleteApp invoked")
	if len(app.Deviceid) < 1 {
		log.Debugf("valid app:", app.Appname)
		return nil
	}
	go SendMqAction(append([]Application{}, app), ACTDELETE)
	return nil
}

//sync the device apps
func SyncDeviceapps(deviceid string) error {
	log.Debugln("SyncDeviceapps invoked")
	_apps, err := DBscanBydeviceid(deviceid)
	if err != nil {
		return err
	}
	//to avoid sync when app is under "docker pull" status
	apps := []Application{}
	timenow := time.Now().Unix()

	for _, v := range _apps {
		if v.Status == CREATING {
			matched, _ := regexp.MatchString("^[0-9]+%: [a-z0-9]+", v.Message)
			if matched {
				if lastupdate, err := time.Parse(time.RFC3339, v.Lastupdate); err == nil {
					if timenow-lastupdate.Unix() < 300 {
						log.Infoln(v.Appname, "is pulling image, skip syncing", v)
						continue
					}
				}
			}
		} else if v.Status == PENDING {
			if ok, message := IsDeviceReady(v.Deviceid); !ok {
				log.Infoln(v.Appname, v.Deviceid, message)
				continue
			}
		}
		apps = append(apps, v)
	}

	if len(apps) < 1 || len(apps[0].Appname) < 1 {
		log.Debugf("device %s: no any apps", deviceid)
		return nil
	}
	go SendMqAction(apps, ACTSYNC)
	return nil

}

//updateDB status put into queue
func MqUpdateAppStatus(cmd Mqkubecmd) error {
	mqdbchan <- cmd
	return nil
}

//send application action message to mqtt
func SendMqAction(apps []Application, act string) error {
	if len(apps) < 1 {
		log.Debugf("apps is null")
		return nil
	}
	cmd := AppsToMqtt(apps, act)

	select {
	//get the chan
	case mqchanlimit <- true:
		err := mqtt_publish_mesg(cmd)
		<-mqchanlimit

		if err != nil {
			log.Errorln("mqtt_publish_mesg:", err)
			//mqchan <- cmd
		}
		return nil

	//put message to pool when timeout
	case <-time.After(30 * time.Second):
		log.Errorln("SendMqAction: put message into mq")
		mqchan <- cmd
		return nil
	}
}

func mqtt_publish_mesg(cmdl MqcmdL) error {
	if len(cmdl.Items) < 1 {
		return errors.New("mqcmd items is null")
	}

	if len(cmdl.Items[0].DeviceId) < 1 {
		return errors.New("mqcmd deviceid is null")
	}

	topic := fmt.Sprintf("edgescale/device/%s/app", cmdl.Items[0].DeviceId)
	if os.Getenv("mqtopic") == "v1" {
		topic = fmt.Sprintf("edgescale/kube/devices/%s", cmdl.Items[0].DeviceId)
	}

	m, _ := json.Marshal(cmdl)

	log.Debugln("===========publish message to ", cmdl.Items[0].DeviceId)
	log.Debugf("publish topic: %s", topic)
	log.Debugf("publish message: %s", string(m))
	if !mqcli.IsConnected() {
		mqcli.Disconnect(1000)
		//panic(err)
		InitMqtt()
		time.Sleep(1 * time.Second)
	}
	token := mqcli.Publish(topic, 0, false, string(m))
	if err := token.Error(); err != nil {
		log.Errorln("Publish Error: ", err, string(m))
		return err
	}
	return nil
	/*
		err := mqcli.Publish(&client.PublishOptions{
			QoS:       0,
			TopicName: []byte(topic),
			Message:   []byte(m),
		})
		return err
	*/
}

//send the mqtt message from pool
func MqttListen() {
	var done chan bool
	InitMqtt()
	go func() {
		var m MqcmdL
		for {
			m = <-mqchan
			log.Warnln("send mqtt with bakup pool")
			err := mqtt_publish_mesg(m)
			if err != nil {
				log.Errorln("PubMsgLoop: ", m, err)
			}
			time.Sleep(1 * time.Millisecond)
		}
	}()
	for i := 0; i < 5; i++ {
		go func() {
			var cmd Mqkubecmd
			for {
				cmd = <-mqdbchan
				if cmd.Type == ACTDELETE {
					err := DBdeviceDeleteApp(cmd)
					if err != nil {
						log.Errorln("mqhandler", cmd.Type, err)
						if strings.Contains(err.Error(), "conditional") {
							log.Infoln("Trying to recovery application", cmd.Podname)
							_ = SyncDeviceapps(cmd.DeviceId)
						} else {
							log.Warnln("Repost DBdeviceDeleteApp", cmd, err)
							time.Sleep(300 * time.Millisecond)
							_ = DBdeviceDeleteApp(cmd)
						}
					}

				} else if cmd.Type == ACTSTATUS {
					err := DBdeviceUpdateApp(cmd)
					if err != nil {
						log.Errorln("mqhandler", cmd.Type, err)
						if strings.Contains(err.Error(), "conditional") {
							log.Infoln("Trying to delete unexpected application", cmd.Podname)
							_ = MQdeleteApp(Application{
								Appname:  cmd.Podname,
								Deviceid: cmd.DeviceId,
							})
							time.Sleep(300 * time.Millisecond)
							_ = SyncDeviceapps(cmd.DeviceId)
						} else {
							log.Warnln("Repost DBdeviceUpdateApp: ", cmd, err)
							time.Sleep(300 * time.Millisecond)
							_ = DBdeviceUpdateApp(cmd)
						}
					}
				}
			}
		}()
	}
	<-done
}
