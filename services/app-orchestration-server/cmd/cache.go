// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"time"

	"github.com/patrickmn/go-cache"
)

var Cdev *cache.Cache
var Capp *cache.Cache
var CTask *cache.Cache
var CDevStatus *cache.Cache
var CIp *cache.Cache

func InitCache() {
	// Create a cache with a default expiration time of 15 minutes, and which
	// purges expired items every 30 minutes
	Cdev = cache.New(120*time.Minute, 200*time.Minute)
	Capp = cache.New(30*time.Minute, 50*time.Minute)
	CTask = cache.New(5*time.Minute, 10*time.Minute)
	CDevStatus = cache.New(1*time.Minute, 2*time.Minute)
	CIp = cache.New(10*time.Minute, 20*time.Minute)
	log.Infoln("Success to Create memeory cache")
}

func CacheAddDev(deviceid string, app Application) {
	log.Debugln("CacheAddDev invoked", deviceid)
	var mapp = make(map[string]Application)
	x, found := Cdev.Get(deviceid)
	if found {
		mapp = x.(map[string]Application)
		a, ok := mapp[app.Appname]
		if ok {
			if len(app.Cfgfactory) < 20 {
				log.Debugln("CacheAddDev using previous factory")
				app.Cfgfactory = a.Cfgfactory
				app.Userid = a.Userid
			}
			if len(app.Createtime) < 5 {
				app.Createtime = a.Createtime
			}
		}
		mapp[app.Appname] = app
		log.Debugln("CacheAddDev: update existing cache", deviceid, len(mapp))
		Cdev.Set(deviceid, mapp, cache.DefaultExpiration)
	} else {
		// adding it even the app is null
		mapp[app.Appname] = app
		log.Debugln("CacheAddDev: Adding new cache", deviceid, len(mapp))
		Cdev.Set(deviceid, mapp, cache.DefaultExpiration)
	}
}

func CacheDelDev(deviceid string, app Application) {
	log.Debugln("CacheDelDev invoked", deviceid)
	x, found := Cdev.Get(deviceid)
	if found {
		mapps := x.(map[string]Application)
		delete(mapps, app.Appname)
		if len(mapps) < 1 {
			log.Debugln("CacheDelDev clear key:", deviceid, app.Appname)
			Cdev.Delete(deviceid)
		} else {
			log.Debugln("CacheDelDev update and del:", deviceid, app.Appname)
			Cdev.Set(deviceid, mapps, cache.DefaultExpiration)
		}

	} else {
		log.Debugln("CacheDelDev not found", deviceid)
	}
}

func CacheCleanDev(deviceid string) {
	log.Debugln("CacheCleanDev invoked", deviceid)
	Cdev.Delete(deviceid)
}

func CacheGetDev(deviceid string) ([]Application, bool) {
	log.Debugln("CachGetlDev invoked", deviceid)
	//var mapps = make(map[string]Application)
	var apps []Application

	x, found := Cdev.Get(deviceid)
	if found {
		mapps := x.(map[string]Application)
		for _, v := range mapps {
			if len(v.Appname) > 1 && len(v.Deviceid) > 1 && v.Status != DELETED {
				apps = append(apps, v)
				if len(v.Cfgfactory) < 20 {
					log.Debugf("CacheGetDev invalid application reload it", v)
					found = false
				}
			}
		}
		log.Debugf("CacheGetDev key %s: num: %v", deviceid, len(apps))

	} else {
		log.Debugln("CacheGetDev key not found", deviceid)
	}
	return apps, found
}

func CacheAddApp(userid string, app Application) {
	log.Debugln("CacheAddApp invoked", userid)
	var mapp = make(map[string]Application)
	x, found := Capp.Get(userid)
	if found {
		mapp = x.(map[string]Application)
		a, ok := mapp[app.Appname+app.Deviceid]
		if ok {
			if len(app.Cfgfactory) < 20 {
				log.Debugln("CacheAddApp using previous factory")
				app.Cfgfactory = a.Cfgfactory
				app.Userid = a.Userid
			}
			if len(app.Createtime) < 5 {
				app.Createtime = a.Createtime
			}
		}
		if userid == app.Userid {
			mapp[app.Appname+app.Deviceid] = app
			log.Debugln("CacheAddApp: update existing cache", userid, len(mapp))
			Capp.Set(userid, mapp, cache.DefaultExpiration)
		}
	} else {
		//if len(app.Appname) > 2 && app.Userid == userid {
		mapp[app.Appname+app.Deviceid] = app
		log.Debugln("CacheAddApp: Adding new cache", userid, len(mapp))
		Capp.Set(userid, mapp, cache.DefaultExpiration)
		//}
	}
}

func CacheDelApp(userid string, app Application) {
	log.Debugln("CacheDelApp invoked", userid)

	x, found := Capp.Get(userid)
	if found {
		mapps := x.(map[string]Application)
		delete(mapps, app.Appname+app.Deviceid)
		if len(mapps) < 1 {
			log.Debugln("CacheDelApp clear key:", userid, app.Appname)
			Capp.Delete(userid)
		} else {
			log.Debugln("CacheDelApp update and del:", userid, app.Appname)
			Capp.Set(userid, mapps, cache.DefaultExpiration)
		}

	} else {
		log.Debugln("CacheDelApp not found", userid)
	}
}

func CacheCleanApp(userid string) {
	log.Debugln("CacheCleanApp invoked", userid)
	Capp.Delete(userid)
}

func CacheGetApp(userid string) ([]Application, bool) {
	log.Debugln("CachGetlApp invoked", userid)
	//var mapps = make(map[string]Application)
	var apps []Application

	x, found := Capp.Get(userid)
	if found {
		mapps := x.(map[string]Application)
		for _, v := range mapps {
			if len(v.Appname) > 1 && len(v.Deviceid) > 1 && v.Status != DELETED {
				apps = append(apps, v)
			}
		}
		log.Debugf("CacheGetApp key %s: num: %v", userid, len(apps))

	} else {
		log.Debugln("CacheGetApp key not found", userid)
	}
	return apps, found
}

func CacheAddTaskSum(taskid string, sum TaskSum, d time.Duration) {
	log.Debugln("CacheAddTask invoked", taskid)
	CTask.Set(taskid, sum, d)
}

func CacheGetTaskSum(taskid string) (TaskSum, bool) {
	if x, ok := CTask.Get(taskid); ok {
		log.Debugf("CacheGetTask %s: %v", taskid, x.(TaskSum))
		return x.(TaskSum), ok
	}
	return TaskSum{}, false
}

func CacheCleanTaskSum(id string) {
	log.Debugln("CacheCleanTaskSum invoked", id)
	CTask.Delete(id)
}

func CacheAddDevStatus(devid string, v DeviceInfo, d time.Duration) {
	log.Debugln("CacheAddDevStatus invoked", devid)
	CDevStatus.Set(devid, v, d)
}

func CacheGetDevStatus(devid string) (DeviceInfo, bool) {
	if x, ok := CDevStatus.Get(devid); ok {
		log.Debugf("CacheGetDevStatus %s: %v", devid, x.(DeviceInfo))
		return x.(DeviceInfo), ok
	}
	return DeviceInfo{}, false
}

func CacheGetIp(devid string) (string, bool) {
	if x, ok := CIp.Get(devid); ok {
		//log.Debugf("CacheGetIp %s: %s", devid, x.(string))
		return x.(string), ok
	}
	return "", false
}

func CacheAddIp(devid, v string, d time.Duration) {
	log.Debugln("CachAddIp invoked", devid)
	CIp.Set(devid, v, d)
}

func CacheDelIp(devid string) {
	log.Debugln("CachDelIp invoked", devid)
	CIp.Delete(devid)
}

func CacheFlush(uid string) {
	log.Debugln("CachFlush invoked userid", uid)
	CacheCleanApp(uid)
	CTask.Flush()
	CDevStatus.Flush()
	CIp.Flush()
}
