// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"bufio"
	"os"
	"strings"
	"time"
)

var applogspath string
var allowedcert []string

func InitStore() {
	applogspath = *logdir + "/apps/"
	/*
		applogspath ~ doesn't work, so use exec
		cmd := fmt.Sprintf("mkdir -p %s", applogspath)
		ret, err = exec.Command("sh", "-c", cmd).Output()
		log.Infoln("InitStore", ret)
	*/
	err := os.MkdirAll(applogspath, 0770)
	if err != nil {
		log.Errorln("InitStore", err)
	}
	if _, err = os.Stat(*logdir + "/certs/allowed"); os.IsNotExist(err) {
		_ = os.MkdirAll(*logdir+"/certs/", 0770)
		f, err := os.Create(*logdir + "/certs/allowed")
		if err != nil {
			log.Errorln(err)
		}
		defer f.Close()
		//	sn := "d9a1aedfad8401a24bf6cce3b1d30968974c017\n"
		//	sn += "48beb98186f51766a5aa8264bc7427bbbfa57e6\n"
		//	sn += "c97f8cdb9a39dee38848b2f68d1addfc6c972493\n"
		sn := "619941602018906756061655201410546986120499551971\n"
		sn += "68381742032723299974103735817487502431562831718\n"
		sn += "53984536866811005513911517931063143703966384546\n"
		f.WriteString(sn)
		f.Sync()
	}
	LoadCerts()

}

func LoadCerts() {
	allowedcert = nil
	f, err := os.Open(*logdir + "/certs/allowed")
	if err != nil {
		log.Errorln(err)
	}
	defer f.Close()
	scanner := bufio.NewScanner(f)

	for scanner.Scan() {
		if len(scanner.Text()) > 2 {
			allowedcert = append(allowedcert, scanner.Text())
		}
	}
	log.Println("allowed cert: ", allowedcert)
}

//actually event log
func AppCreateLog(app Application) {
	if len(app.Appname) < 2 || len(app.Userid) < 1 {
		return
	}
	n := app.Appname + "_" + app.Userid
	c := time.Now().Format(time.RFC3339) + ": " + app.Status + " "
	c += app.Deviceid + " " + app.Message
	CreateLog(n, c)

}

//actually event log
func AppUpdateLog(app Application) {
	if len(app.Appname) < 2 || len(app.Userid) < 1 {
		return
	}
	n := app.Appname + "_" + app.Userid
	c := time.Now().Format(time.RFC3339) + ": "
	c += app.Status + " " + app.Message
	UpdateLog(n, c, os.O_APPEND|os.O_WRONLY|os.O_CREATE)
}

//docker instance log
func SaveDockerLog(appname, content string) {
	n := appname + ".log"
	if strings.HasPrefix(content, "pod \""+appname) &&
		(strings.HasSuffix(content, "does not exist\n") ||
			strings.HasSuffix(content, "does not exist")) {
		content = "app instance \"" + appname + "\" " + "does not exist or start"
	}
	UpdateLog(n, content, os.O_WRONLY|os.O_CREATE)
}

/*
func AppGetLog(app Application) string {
	n := app.Appname + "_" + app.Userid
	f, err := os.Open(applogspath + n)
	if err != nil {
		log.Errorln("GetLog", name, err)
		return ""
	}
	defer f.Close()
	return ""
}
*/
func CreateLog(name, content string) {
	f, err := os.Create(applogspath + name)
	if err != nil {
		log.Errorln("CreateLog", name, err)
		return
	}
	defer f.Close()
	f.WriteString(content + "\n")
	f.Sync()
}

func UpdateLog(name, content string, flag int) {
	f, err := os.OpenFile(applogspath+name, flag, 0660)
	if err != nil {
		log.Errorln("UpdateLog", name, err)
		return
	}
	defer f.Close()
	f.WriteString(content + "\n")
	f.Sync()
}
