// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"errors"
	"regexp"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/dynamodb"
)

const (
	//DEVICETABLE = "edgescale_device_status"
	CONFIGTABLE = "edgescale_config"
)

var db *dynamodb.DynamoDB

func InitDynamoDb() {
	// create an aws session
	sess := session.Must(session.NewSessionWithOptions(session.Options{
		SharedConfigState: session.SharedConfigEnable,
	}))
	if dynamoEnd != nil && len(*dynamoEnd) > 1 {
		sess.Config.Endpoint = dynamoEnd
	}
	// create a dynamodb instance
	db = dynamodb.New(sess)
	//InitCache()
}

func DBcreateApp(app Application) error {

	log.Debugln("DBcreateApp invoked")

	if ok, message := IsDeviceReady(app.Deviceid); !ok {
		app.Message = message
	}

	err := CreateApp(app)
	if err != nil {
		log.Infoln("DB CLi create_item: ", err)
	} else {
		CacheCleanDev(app.Deviceid)
		//clean user app cache
		_, found := Capp.Get(app.Userid)
		if found {
			CacheAddApp(app.Userid, app)
		} else {
			CacheCleanApp(app.Userid)
		}
	}
	AppCreateLog(app)
	return err
}

func DBdelItem(app Application) error {
	log.Debugln("DBdelItem invoked")

	err := DeleteApp(app)
	if err != nil {
		log.Errorln("DB CLi delappbyname: ", app.Appname, err)
	} else {
		app.Status = DELETED

		CacheDelDev(app.Deviceid, app)
		CacheDelApp(app.Userid, app)
		go AppUpdateLog(app)
	}
	return err
}

//http handler to delete application
func DBsetappstatus(appname, userid, appstatus string) (Application, error) {
	var app Application
	log.Debugln("DBsetappstatus invoked", appname, appstatus)
	// create the api params

	apps, err := DBscanByAppname(appname, userid)
	if err != nil {
		return app, err
	}
	if len(apps) < 1 {
		return app, errors.New("no thus app")
	}
	return DBUpdateStatusOnly(apps[0], appstatus)
}

func DBqueryappbyuser(usrid string) ([]Application, error) {
	var apps []Application

	log.Debugln("DBqueryappbyuser invoked")

	cacheapps, found := CacheGetApp(usrid)
	if found {
		for _, v := range cacheapps {
			if len(v.Appname) > 1 {
				apps = append(apps, v)
			}
		}
		log.Debugln("DBqueryappbyuser cache exists:", usrid)
		return apps, nil
	}

	log.Debugf("GetAppByUser read from pg")
	apps, err := GetAppsByUser(usrid)
	if err != nil {
		return apps, err
	}

	// Add user's app to cache
	if len(apps) == 0 { //userid apps nothing
		CacheAddApp(usrid, Application{})

	} else { //userid apps into cache
		for _, a := range apps {
			CacheAddApp(usrid, a)
		}
	}
	return apps, err
}

//query specific app not used so far, but use scan
func DBqueryapp(appname, deviceid string) ([]Application, error) {
	var app []Application
	log.Debugln("DBqueryspecfic App invoked")

	app, err := GetAppsByNameAndDeviceId(appname, deviceid)
	return app, err
}

//device update app status vai mqtt protocal
func DBdeviceUpdateApp(data Mqkubecmd) error {
	log.Debugln("DBdeviceUpdateApp invoked", data.Podname)
	// create the api params

	//Workaround for status report bug on device
	//Pending status is the bypass status which is required to be processed on device furthur, but it is not done
	if strings.Contains(data.Podmessage, "PLEG") ||
		strings.Contains(data.Podmessage, "No such container") {
		return nil
	}
	if len(data.Podmessage) > 10 {
		if strings.Contains(data.Podmessage, "Error") {
			if data.Podstatus == CREATING {
				data.Podstatus = FAILED
			}
		} else if len(data.Podmessage) > 200 {
			data.Podstatus = STARTING
		}
	} else if len(data.Podmessage) < 2 {
		if data.Podstatus == CREATING {
			//invalid message
			return nil
		} else {
			data.Podmessage = data.Podstatus
		}
	}

	if len(data.Body) < 2 {
		data.Body = data.Podstatus
	}

	//Workaround for status report bug on device
	//Pending status is the bypass status which is required to be processed on device furthur, but it is not done
	if data.Podstatus == "Pending" ||
		strings.Contains(data.Podmessage, "Image Download complete: 100") {
		data.Podstatus = STARTING
		data.Podmessage = "Download image done, app is starting."
	}
	app := Application{
		Appname:    data.Podname,
		Deviceid:   data.DeviceId,
		Status:     data.Podstatus,
		Message:    data.Podmessage,
		Lastupdate: time.Now().Format(time.RFC3339),
	}

	devapps, found := CacheGetDev(data.DeviceId)
	if found {
		for _, v := range devapps {
			if app.Appname == v.Appname {
				if app.Status == v.Status &&
					(app.Message == v.Message ||
						(len(app.Message) > 40 && len(v.Message) > 40 &&
							app.Message[0:15] == v.Message[0:15])) {
					log.Debugln("DBdeviceUpdateApp, cache existed, no changes")
					return nil
				} else if app.Status == CREATING && v.Status == CREATING {
					matched, _ := regexp.MatchString("^[0-9]+%: [a-z0-9]+", v.Message)
					if matched {
						if lastupdate, err := time.Parse(time.RFC3339, v.Lastupdate); err == nil {
							if time.Now().Unix()-lastupdate.Unix() < 20 {
								log.Infoln(v.Appname, "update cache only", v.Message)
								//CacheAddDev(app.Deviceid, app)
								_, found := Capp.Get(app.Userid)
								if found {
									CacheAddApp(app.Userid, app)
								}
								return nil
							}
						}

					}
				}
			}
		}
	}

	err := UpdateApp(app)
	if err != nil {
		log.Errorln("DBDevice update: ", err, data, app)
	}
	application, err := GetAppByNameAndDeviceId(app.Appname, app.Deviceid)
	if err != nil {
		log.Errorf("DBDevice get app by name and deviceId failed, %s, %s", app.Appname, app.Deviceid)
	}
	app = application

	CacheCleanDev(app.Deviceid)
	//remove cache to make sync
	_, found = Capp.Get(app.Userid)
	if found {
		CacheAddApp(app.Userid, app)
	} else {
		CacheCleanApp(app.Userid)
	}

	go AppUpdateLog(app)
	return err
}

func DBdeviceDeleteApp(data Mqkubecmd) error {
	log.Debugln("DBdeviceDeleteApp invoked", data.Podname)

	app := Application{
		Appname:    data.Podname,
		Deviceid:   data.DeviceId,
		Status:     data.Podstatus,
		Message:    data.Podmessage,
		Lastupdate: time.Now().Format(time.RFC3339),
	}

	err := AppSetDelete(app)
	if err != nil {
		log.Errorln("DBdeviceDeleteApp set app status and message to DELETED is failed: ", err, app)
		return err
	}

	app, err = GetAppByNameAndDeviceId(app.Appname, app.Deviceid)
	if err != nil {
		log.Errorln("DBdeviceDeleteApp get app with appname and deviceid is failed: ", err)
		return err
	}

	go AppUpdateLog(app)
	return err
}

//user used to update app status Eg create/delete
func DBUpdateStatusOnly(app Application, appstatus string) (Application, error) {
	log.Debugln("DBUpdateStatusOnly invoked")
	// create the api params

	app.Lastupdate = time.Now().Format(time.RFC3339)
	err := UpdateAppStatus(app, appstatus)
	if err != nil {
		log.Errorln("update app status is failed: ", err, app)
		return app, err
	}

	app, err = GetAppByNameAndDeviceId(app.Appname, app.Deviceid)
	if err != nil {
		log.Errorln("DB Query UnmarshalListOfMaps: ", err)
	} else {
		CacheCleanDev(app.Deviceid)
		if app.Status == DELETED {
			CacheDelApp(app.Userid, app)
		} else {
			_, found := Capp.Get(app.Userid)
			if found {
				CacheAddApp(app.Userid, app)
			} else {
				CacheCleanApp(app.Userid)
			}
		}
	}
	go AppUpdateLog(app)
	return app, err

}

// query the spefic application
func DBscanByAppname(appname, userid string) ([]Application, error) {
	// create the api params
	var apps []Application

	dbapps, err := DBqueryappbyuser(userid)
	if err != nil {
		return apps, err
	}

	for _, v := range dbapps {
		if v.Appname == appname {
			apps = append(apps, v)
		}
	}
	return apps, nil
}

// query device application
func DBscanBydeviceid(deviceid string) ([]Application, error) {
	log.Debugln("DBscanBydeviceid invoked", deviceid)

	apps, found := CacheGetDev(deviceid)
	if found {
		log.Debugln("DBscanBydeviceid Using cache", deviceid, apps)
		return apps, nil
	}
	log.Debugln("DBscanBydeviceid rescan ", deviceid)

	apps, err := ScanByDeviceId(deviceid)
	if err != nil {
		log.Fatalln("ScanByDeviceId with pg is failed.")
		return apps, err
	}

	if len(apps) == 0 {
		CacheAddDev(deviceid, Application{})
	} else {
		for _, a := range apps {
			CacheAddDev(deviceid, a)
		}
	}

	return apps, err
}

//query device ip address
func DBqueryDevice(deviceid string) ([]DeviceInfo, error) {
	var devs []DeviceInfo

	devStatus, found := CacheGetDevStatus(deviceid)
	if found {
		log.Debugln("DBqueryDevice Using cache", deviceid, devStatus)
		devs = append(devs, devStatus)
		return devs, nil
	}

	log.Debugln("DBqueryDevice invoked", deviceid)

	devs, err := GetDeviceStatusFromRedis(deviceid)
	if err != nil {
		return make([]DeviceInfo, 0), err
	}

	if len(devs) > 0 {
		for _, v := range devs {
			CacheAddDevStatus(deviceid, v, 1*time.Minute)
		}
	} else {
		CacheAddDevStatus(deviceid, DeviceInfo{}, 1*time.Minute)
	}
	return devs, err
}
