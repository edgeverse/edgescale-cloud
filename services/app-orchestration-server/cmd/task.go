// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import ( //b64 "encoding/base64"
	//"github.com/yosssi/gmq/mqtt"
	//"github.com/yosssi/gmq/mqtt/client"

	"errors"
	"fmt"
	_ "io/ioutil"
	"math/rand"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"
	"github.com/buger/jsonparser"
)

const (
	TASKTABLE = "edgescale-app-task"
)

var taskchan []chan TaskInfo = []chan TaskInfo{
	make(chan TaskInfo, 10000),
	make(chan TaskInfo, 10000),
	make(chan TaskInfo, 10000),
}

var delappch chan Application = make(chan Application, 100000)

var StatusList = []string{PENDING, CREATING, STARTING, RUNNING, DELETING, REBOOTING, DELETED}

func DBGroupInQueue(task TaskInfo) error {
	log.Debugln("DBGroupInQueue:", task.ID)

	TMap, err := dynamodbattribute.MarshalMap(task)
	if err != nil {
		log.Errorln("Cannot marshal application into AttributeValue map", task)
	}
	//log.Debugln(AppMap)
	// create the api params
	params := &dynamodb.PutItemInput{
		TableName: aws.String(TASKTABLE),
		Item:      TMap,
		//ReturnValues: aws.String(dynamodb.ReturnValueNone),
		ConditionExpression: aws.String("NOT #id =:id"),
		ExpressionAttributeNames: map[string]*string{
			"#id": aws.String("id"),
		},
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":id": {
				S: aws.String(task.ID),
			},
		},
	}

	// put the item
	for i := 0; i < 5; i++ {
		_, err = db.PutItem(params)
		if err == nil {
			taskchan[rand.Intn(len(taskchan))] <- task
			return nil
		} else if err != nil && i >= 5 {
			log.Infoln("Task create_item: ", task, err)
			return errors.New(fmt.Sprintf("%v %v", task, err))
		} else {
			time.Sleep(2 * time.Second)
		}
	}
	return nil
}

func DBGetTask(id string) ([]TaskInfo, error) {
	log.Debugln("DBGetTask invoked: ", id)
	var ts []TaskInfo
	params := &dynamodb.QueryInput{
		TableName:              aws.String(TASKTABLE),
		KeyConditionExpression: aws.String("#id = :id"),
		ExpressionAttributeNames: map[string]*string{
			"#id": aws.String("id"),
		},
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":id": {
				S: aws.String(id),
			},
		},
	}
	// read the item
	resp, err := db.Query(params)
	if err != nil {
		log.Infoln("GetTask Query:", id, err)
	}

	err = dynamodbattribute.UnmarshalListOfMaps(resp.Items, &ts)
	if err != nil {
		log.Debugln("GetTask UnmarshalListOfMaps: ", err)
	}
	return ts, err

}
func DBDelTask(id string) error {
	// create the api params
	params := &dynamodb.DeleteItemInput{
		TableName: aws.String(TASKTABLE),
		Key: map[string]*dynamodb.AttributeValue{
			"id": {
				S: aws.String(id),
			},
		},
		ReturnValues: aws.String(dynamodb.ReturnValueNone),
	}
	// delete the item
	_, err := db.DeleteItem(params)
	if err != nil {
		log.Infoln("del tasklist: ", id, err)
	}
	CacheCleanTaskSum(id)
	return err
}

func DBGetTaskList(uid string) ([]TaskInfo, error) {
	var ts []TaskInfo
	params := &dynamodb.ScanInput{
		TableName: aws.String(TASKTABLE),
		//KeyConditionExpression: aws.String("#id = :id"),
		FilterExpression:     aws.String("#id = :id"),
		ProjectionExpression: aws.String("id"),
		ExpressionAttributeNames: map[string]*string{
			"#id": aws.String("uid"),
		},
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":id": {
				S: aws.String(uid),
			},
		},
	}
	// read the item
	resp, err := db.Scan(params)
	if err != nil {
		log.Infoln("GetTask Query:", uid, err)
	}

	err = dynamodbattribute.UnmarshalListOfMaps(resp.Items, &ts)
	if err != nil {
		log.Debugln("GetTask UnmarshalListOfMaps: ", err)
	}
	return ts, err

}

func UpdateTaskStatus(task TaskInfo, header string, code int) error {
	log.Debugln("UpdateTaskStatus invoked status: ", header, code)
	// create the api params

	params := &dynamodb.UpdateItemInput{
		TableName: aws.String(TASKTABLE),
		Key: map[string]*dynamodb.AttributeValue{
			"id": {
				S: aws.String(task.ID),
			},
		},
		UpdateExpression: aws.String(fmt.Sprintf("set %s=:c", header)),
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":c": {N: aws.String(fmt.Sprintf("%d", code))},
		},
		ReturnValues: aws.String(dynamodb.ReturnValueNone),
	}

	// update the item
	_, err := db.UpdateItem(params)
	if err != nil {
		log.Errorln("DB CLi setstatus: ", err, task)
	}
	return err
}

func TaskHandlerLoop() {
	taskchlength := len(taskchan)
	//log.Println(taskchlength)

	for i := 0; i < taskchlength; i++ {
		for j := 0; j < 10; j++ {
			go func(k int) {
				var tsf TaskInfo
				for {
					tsf = <-taskchan[k]
					devnames, err := GetGroupDeviceList(tsf.Groupid)
					if err != nil {
						log.Fatalln("GetGroupDevicelist", tsf, err)
						_ = UpdateTaskStatus(tsf, "ttotal", -2)
						continue
					}
					devlength := len(devnames)
					_ = UpdateTaskStatus(tsf, "ttotal", devlength)
					if devlength == 0 {
						log.Fatalln("Group device list null", tsf.Groupid)
						continue
					}

					b := []byte(tsf.Appcfg)
					basename, err := GetDockerBaseName(b)
					if err != nil {
						log.Fatalln("GetDockerBaseName", tsf, err)
						_ = UpdateTaskStatus(tsf, "ttotal", -3)
					}
					before := time.Now().Unix()
					for k, v := range devnames {
						appname := basename + "-" + string(Genrand(16))
						appmessage := "Wait to schedule and launch"
						cfg, err := UpdateDockerAppCfg(b, appname)
						if err != nil {
							log.Fatalln("UpdateDockerAppCfg", tsf, err)
							appmessage = err.Error()
						}

						timenow := time.Now().Format(time.RFC3339)
						app := Application{
							Appname:  appname,
							Deviceid: v,
							//Cfgfactory: b64.StdEncoding.EncodeToString(cfg),
							Cfgfactory: string(cfg),
							Userid:     tsf.Userid,
							Status:     PENDING,
							Task:       tsf.ID,
							Message:    appmessage,
							Createtime: timenow,
							Lastupdate: timenow,
						}
						err = GroupCreateApp(app)
						if err != nil {
							log.Fatalln("GroupCreateApp", err)

						}
						time.Sleep(5 * time.Millisecond)
						if k%50 == 0 {
							cur := time.Now().Unix()
							if cur-before >= 10 {
								before = cur
								_ = UpdateTaskStatus(tsf, "cur", k)
							}
						}
					}
					_ = UpdateTaskStatus(tsf, "cur", devlength)

				}
			}(i)
		}
	}
	for {
		a := <-delappch
		err := DelApp(a)
		if err != nil {
			if strings.Contains(err.Error(), "provision") {
				time.Sleep(1 * time.Minute)
			}
		}
	}
}

func DelApp(a Application) error {
	app, err := DBsetappstatus(a.Appname, a.Userid, DELETED)
	if err != nil {
		log.Errorln("Func DelApp:", a.Appname, err.Error())
	}

	time.Sleep(10 * time.Millisecond)
	err = MQdeleteApp(app)
	/*
		go func() {
			log.Infoln("DelGroup: Force delete after 30 seconds")
			time.Sleep(30 * time.Second)
			app.Lastupdate = time.Now().Format(time.RFC3339)
			DBUpdateStatusOnly(app, DELETED)
		}()
	*/
	return err
}

func Genrand(size int) []byte {
	kinds, result := [][]int{[]int{48, 10}, []int{97, 26}}, make([]byte, size)
	rand.Seed(time.Now().UnixNano())
	for i := 0; i < size; i++ {
		ikind := rand.Intn(2)
		scope, base := kinds[ikind][1], kinds[ikind][0]
		result[i] = uint8(base + rand.Intn(scope))
	}
	return result
}

func UpdateDockerAppCfg(b []byte, name string) ([]byte, error) {
	b, err := jsonparser.Set(b, []byte(fmt.Sprintf(`"%s"`, name)), "metadata", "name")
	if err != nil {
		return b, err
	}

	b, err = jsonparser.Set(b, []byte(fmt.Sprintf(`"%s"`, name)), "spec", "containers", "[0]", "name")
	if err != nil {
		return b, err
	}
	return b, nil

}

func GetDockerBaseName(b []byte) (string, error) {
	containerimage, err := jsonparser.GetString(b, "spec", "containers", "[0]", "image")
	if err != nil {
		return "", err
	}
	registryL := strings.Split(strings.Split(containerimage, `:`)[0], `/`)
	//basename := registryL[len(registryL)-1] + fmt.Sprintf("-%d", rand.Int(20))
	basename := registryL[len(registryL)-1]
	return basename, nil
}

func GroupCreateApp(app Application) error {
	err := DBcreateApp(app)
	if err != nil {
		if err == AppExist {
			_ = MQcreatApp(app)
		}
		return err
	}
	return MQcreatApp(app)

}
