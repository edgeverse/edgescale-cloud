// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"database/sql"

	"github.com/garyburd/redigo/redis"
	"github.com/jinzhu/gorm"
)

func GetGroupDeviceList(groupId string) (names []string, err error) {
	type Name struct {
		Name string `json:"name"`
	}
	var rs []Name
	err = DB.Table("hosts").Select("hosts.name").
		Joins("INNER JOIN dcca_ass_device_group ON dcca_ass_device_group.device_id=hosts.id").
		Where("dcca_ass_device_group.group_id = ?", groupId).Scan(&rs).Error

	if err != nil {
		log.Errorln("GetGroupDeviceList is failed: ", err)
		return names, ErrDatabase
	}

	for _, v := range rs {
		names = append(names, v.Name)
	}
	return
}

func UpdateAppStatus(app Application, appStatus string) (err error) {
	err = DB.Table(app.TableName()).Where("appname = ? AND deviceid = ?", app.Appname, app.Deviceid).
		Update(Application{Status: appStatus, Lastupdate: app.Lastupdate}).Error
	if err != nil {
		log.Errorln("UpdateAppStatus is Failed: ", err)
		return ErrDatabase
	}
	return
}

func UpdateApp(app Application) (err error) {
	err = DB.Table(app.TableName()).Where("appname = ? AND appstatus != ?", app.Appname, DELETED).
		Update(Application{Status: app.Status, Message: app.Message, Lastupdate: app.Lastupdate}).Error
	if err != nil {
		log.Errorln("UpdateApp is Failed: ", err)
		return ErrDatabase
	}
	return
}

func AppSetDelete(app Application) (err error) {
	err = DB.Table(app.TableName()).
		Where("appname = ? AND deviceid = ? AND appstatus != ?", app.Appname, app.Deviceid, DELETED).
		Update(Application{Status: DELETED, Message: DELETED}).Error
	if err != nil {
		log.Errorln("AppSetDelete is Failed: ", err)
		return ErrDatabase
	}
	return
}

func GetAppByNameAndDeviceId(appName, deviceId string) (app Application, err error) {
	err = DB.Where(&Application{Appname: appName, Deviceid: deviceId}).First(&app).Error
	if gorm.IsRecordNotFoundError(err) {
		return app, AppNotExist
	} else if err != nil {
		log.Errorln("GetAppByNameAndDeviceId is Failed: ", err)
		return app, ErrDatabase
	}
	return
}

func GetAppsByNameAndDeviceId(appName, deviceId string) (apps []Application, err error) {
	err = DB.Where(&Application{Appname: appName, Deviceid: deviceId}).Find(&apps).Error
	if err != nil {
		log.Errorln("GetAppsByNameAndDeviceId is Failed: ", err)
		return apps, ErrDatabase
	}
	return
}

func GetAppsByUser(userId string) (apps []Application, err error) {
	err = DB.Where("userid = ? AND appstatus != ?", userId, DELETED).
		Select("appname, deviceid, appstatus, appmessage, userid, appcreatetime, lastupdate, task").
		Find(&apps).Error
	if err != nil {
		log.Errorln("GetAppsByUser is Failed: ", err)
		return apps, ErrDatabase
	}
	return
}

func ScanByDeviceId(deviceId string) (apps []Application, err error) {
	err = DB.Where("deviceid = ? AND appstatus != ?", deviceId, DELETED).
		Select("appname, deviceid, appstatus, userid, appmessage, lastupdate, cfgfactory, task").
		Find(&apps).Error
	if err != nil {
		log.Errorln("ScanByDeviceId is Failed: ", err)
		return apps, ErrDatabase
	}
	return
}

func CreateApp(app Application) (err error) {
	var appStatus string
	err = DB.Table("edgescale_app").Where("appname = ? AND deviceid = ?", app.Appname, app.Deviceid).
		Select("appstatus").Row().Scan(&appStatus)

	if err == sql.ErrNoRows {
		err = DB.Create(&app).Error
		if err != nil {
			log.Errorln("CreateApp create app is failed: ", err)
			return ErrDatabase
		}
		return
	} else if err != nil {
		log.Errorln("CreateApp select app by appname and deviceid is failed: ", err)
		return ErrDatabase
	}

	if appStatus == DELETED {
		updateApp := &Application{
			Userid:     app.Userid,
			Cfgfactory: app.Cfgfactory,
			Status:     app.Status,
			Message:    app.Message,
			Createtime: app.Createtime,
			Lastupdate: app.Lastupdate,
			Task:       app.Task,
			Reason:     app.Reason,
		}
		err = DB.Model(&app).Where("appname = ? AND deviceid = ?", app.Appname, app.Deviceid).
			Update(updateApp).Error
		if err != nil {
			log.Errorln("CreateApp update app is failed: ", err)
			return ErrDatabase
		}
		return
	}

	return AppExist
}

func DeleteApp(app Application) (err error) {
	err = DB.Delete(&Application{Appname: app.Appname, Deviceid: app.Deviceid, Status: DELETED}).Error
	if err != nil {
		log.Errorln("DeleteApp is failed: ", err)
		return ErrDatabase
	}
	return
}

func GetDeviceStatusFromRedis(deviceId string) (devices []DeviceInfo, err error) {
	conn := RedisPool.Get()
	defer conn.Close()
	values, err := redis.StringMap(conn.Do("hgetall", deviceId))
	if err != nil {
		log.Errorln("GetDeviceStatusFromRedis is failed: ", err)
		return devices, ErrRedis
	}

	if len(values) == 0 {
		return devices, nil
	}

	deviceInfo := DeviceInfo{
		Deviceid:   deviceId,
		DiskU:      values["MemUsage"],
		DiskF:      values["DiskFree"],
		LastReport: values["Timestamp"],
		CpuUsage:   values["CPUUsage"],
		MemUsage:   values["MemUsage"],
		AppNum:     values["AppNumber"],
		EsVersion:  values["EsVersion"],
		IpAddr:     values["IpAddr"],
	}

	devices = append(devices, deviceInfo)
	return devices, nil
}
