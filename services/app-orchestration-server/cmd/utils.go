// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	//b64 "encoding/base64"
	//"github.com/yosssi/gmq/mqtt"
	//"github.com/yosssi/gmq/mqtt/client"

	"fmt"
	_ "io/ioutil"
	"math/rand"
	"strconv"
	"strings"
	"time"
)

func AppMeetTask(app Application, id string) bool {
	if id == "" {
		return true
	} else {
		return app.Task == id
	}
}
func AppMeetDevice(app Application, id string) bool {
	if id == "" {
		return true
	} else {
		return app.Deviceid == id
	}
}

func AppMeetUser(app Application, id string) bool {
	if id == "" {
		return true
	} else {
		return app.Userid == id
	}
}

func AppMeetStatus(app Application, id string) bool {
	if id == "" {
		return true
	} else {
		if id[0:1] == `!` {
			return app.Status != id[1:]
		}
		return app.Status == id
	}
}

func InAppSums(n string, as []ApplicationSum) (int, bool) {
	for k, v := range as {
		if n == v.Name {
			return k, true
		}
	}
	return 0, false
}

func IsDeviceReady(deviceid string) (bool, string) {
	tofloat := func(s string) float64 {
		if len(s) > 1 {
			n := strings.Split(strings.Split(s, "%")[0], " ")[0]
			if s, err := strconv.ParseFloat(n, 64); err == nil {
				return s
			}
		}
		return 1
	}

	devs, err := DBqueryDevice(deviceid)
	if err != nil {
		return false, err.Error()
	}
	if len(devs) < 1 {
		return false, deviceid + ":null"
	}

	devstatus := devs[0]

	//85% CPU or memory are used
	if tofloat(devstatus.MemUsage) > 85 {
		return false, "Out of Memory, Used:" + devstatus.MemUsage
	}
	if tofloat(devstatus.CpuUsage) > 85 {
		return false, "Out of CPU, Used:" + devstatus.CpuUsage
	}

	free := tofloat(devstatus.DiskF)
	used := tofloat(devstatus.DiskU)
	//95% storage are used
	if free/(free+used) < 0.05 {
		return false, fmt.Sprintf("Out of Disk, Used:%s Free:%s", devstatus.DiskU, devstatus.DiskF)
	}
	return true, ""
}

func GenrandInt(size int) []byte {
	kinds, result := [][]int{[]int{48, 10}, []int{97, 6}}, make([]byte, size)
	rand.Seed(time.Now().UnixNano())
	for i := 0; i < size; i++ {
		ikind := rand.Intn(2)
		scope, base := kinds[ikind][1], kinds[ikind][0]
		result[i] = uint8(base + rand.Intn(scope))
	}
	return result
}
