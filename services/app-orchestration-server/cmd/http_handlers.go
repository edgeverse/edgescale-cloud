// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	//b64 "encoding/base64"
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/buger/jsonparser"
	"github.com/gorilla/mux"
)

const dns1123LabelFmt string = "[a-z0-9]([-a-z0-9]*[a-z0-9])?"

type HandlerFunc func(http.ResponseWriter, *http.Request)

type ErrorResp struct {
	Code       int    `json:"code"`
	ApiVersion string `json:"apiVersion"`
	Error      bool   `json:"error"`
	Message    string `json:"message"`
}

type SuccessResp struct {
	Code       int    `json:"code"`
	ApiVersion string `json:"apiVersion"`
	Message    string `json:"status"`
}

func (a Apps) Len() int {
	return len(a)
}
func (a Apps) Less(i, j int) bool {
	t1, err := time.Parse(time.RFC3339, a[i].Createtime)
	if err != nil {
		return true
	}
	t2, err := time.Parse(time.RFC3339, a[j].Createtime)
	if err != nil {
		return true
	}
	return time.Since(t1).Seconds() < time.Since(t2).Seconds()
}
func (a Apps) Swap(i, j int) {
	a[i], a[j] = a[j], a[i]
}

func makeHandler(fn func(http.ResponseWriter, *http.Request)) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if len(r.TLS.PeerCertificates) > 0 {
			username := r.TLS.PeerCertificates[0].Subject.CommonName
			sn := r.TLS.PeerCertificates[0].SerialNumber.String()
			for _, v := range allowedcert {
				if sn == v {
					fn(w, r)
					return
				}
			}
			log.Errorln("User:", username, "Serial Number:", sn, "don't have permission to access")
			respondError(w, http.StatusUnauthorized, username+": don't have permission to access!")
			//fn(w, r)
			return
		} else {
			respondError(w, http.StatusInternalServerError, "PeerCertificates Error")
		}
	}
}

func respondJSON(w http.ResponseWriter, status int, payload interface{}) {
	response, err := json.Marshal(payload)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(err.Error()))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	w.Write([]byte(response))
}

func respondError(w http.ResponseWriter, code int, message string) {
	log.Debugln("Http respondError:", code, message)
	respondJSON(w, code, ErrorResp{
		Code:       code,
		ApiVersion: APIVERSION,
		Message:    message,
		Error:      true})
}

func respondSucess(w http.ResponseWriter, message string) {
	log.Debugln("Http respondSuccess:", message)
	respondJSON(w, 200, SuccessResp{
		Code:       0,
		ApiVersion: APIVERSION,
		Message:    message})
}

func GetNodeIp(devid string) string {

	if len(devid) < 1 {
		return ""
	}
	if v, ok := CacheGetIp(devid); ok {
		return v
	}
	if v, ok := NodeInKube(devid); ok {
		for _, vv := range v.Status.Addresses {
			if vv.Type == "InternalIP" {
				CacheAddIp(devid, vv.Address, 15*time.Minute)
				return vv.Address
			}
		}
	}
	devs, err := DBqueryDevice(devid)
	if err == nil {
		for _, v := range devs {
			CacheAddIp(devid, v.IpAddr, 15*time.Minute)
			return v.IpAddr
		}
	}
	CacheAddIp(devid, "", 10*time.Minute)
	return ""
}

func FormatStatus(s string) string {
	switch s {
	case PENDING:
		return "Pending"
	case CREATING:
		return "Creating"
	case RUNNING:
		return "Running"
	case STARTING:
		return "Starting"
	case FAILED:
		return "Failed"
	case DELETING:
		return "Deleting"
	default:
		return s
	}
}

func AppsToHttp(apps []Application) RespHttpList {
	//log.Debugln("To http len:", len(apps))
	r := make([]RespHttp, len(apps))
	for i, v := range apps {
		r[i].Meta.CreationTimestamp = v.Createtime
		r[i].Meta.Name = v.Appname
		r[i].Meta.NodeName = v.Deviceid
		r[i].Status.Phase = FormatStatus(v.Status)
		r[i].Status.HostIP = GetNodeIp(v.Deviceid)
		r[i].Status.Message = v.Message
		r[i].Status.Reason = v.Reason

		if v.Status == RUNNING {
			r[i].Status.Reason = ""
			r[i].Status.Message = fmt.Sprintf("Started At: %s", v.Lastupdate)

		} else if strings.Contains(v.Message, "Error") {
			if strings.Contains(v.Message, "CrashLoopBackOff") {
				r[i].Status.Reason = "Error: CrashLoopBackOff"
			} else if strings.Contains(v.Message, "ImagePullBackOff") {
				r[i].Status.Reason = "Error: ImagePull"
			} else if strings.Contains(v.Message, "ErrImagePull") {
				r[i].Status.Reason = "Error: ImagePull"
			} else if strings.Contains(v.Message, "Container Failed") {
				r[i].Status.Reason = "Error: Start Container Failed"
			} else {
				r[i].Status.Reason = "Error"
			}
		} else if len(v.Message) < 5 || v.Message == "null" {
			r[i].Status.Message = fmt.Sprintf("%s on device %s", v.Status, v.Deviceid)
		}
	}
	return RespHttpList{
		Code:       0,
		Offset:     0,
		Limit:      1,
		Total:      len(r),
		ApiVersion: APIVERSION,
		Items:      r,
	}
}

// Test
func HealthcheckHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "%v\n", "ok")
}

func CheckPodcfg(b []byte, ispod bool) error {
	var js map[string]interface{}

	if err := json.Unmarshal(b, &js); err != nil {
		return errors.New(err.Error())
	}

	apiversion, err := jsonparser.GetString(b, "apiVersion")
	if err != nil || apiversion != "v1" {
		return errors.New("BadRequest: apiVersion wrong")
	}

	containerimage, err := jsonparser.GetString(b, "spec", "containers", "[0]", "image")
	if err != nil || len(containerimage) < 2 {
		return errors.New("BadRequest: wrong container image")
	}

	kind, err := jsonparser.GetString(b, "kind")
	if err != nil || kind != "Pod" {
		return errors.New("BadRequest: kind wrong")
	}
	/*
		deviceid, err := jsonparser.GetString(b, "spec", "nodeSelector", "kubernetes.io/hostname")
		if err != nil || len(deviceid) < 1 {
			return errors.New("wrong nodeSelector" + err.Error())
		}
	*/
	name, err := jsonparser.GetString(b, "metadata", "name")
	if err != nil {
		return errors.New("metadata/name" + err.Error())
	}
	hostpath, _, _, err := jsonparser.Get(b, "spec", "volumes", "[0]", "hostPath", "path")
	if err == nil && len(hostpath) == 0 {
		return errors.New("BadRequest: volume")
	}

	conport, _, _, err := jsonparser.Get(b, "spec", "containers", "[0]", "ports", "[0]", "containerPort")
	if err == nil && len(conport) == 0 {
		return errors.New("BadRequest: containers->ports")
	}

	if ispod {
		dns1123LabelRegexp := regexp.MustCompile("^" + dns1123LabelFmt + "$")

		if !dns1123LabelRegexp.MatchString(name) {
			return errors.New("Invalid app name: must use character [0-9a-z] or -")
		}

		labelname, err := jsonparser.GetString(b, "metadata", "labels", "name")
		if err != nil {
			return errors.New("metadata/label" + err.Error())
		} else if err == nil && len(labelname) > 1 {
			if !dns1123LabelRegexp.MatchString(labelname) {
				return errors.New("Invalid labelname: must use character [0-9a-z] or -")
			}
		}
	}
	return nil
}

// Create app instance
func CreateAppHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)

	log.Infoln("CreateAppHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)

	defer r.Body.Close()
	b, _ := ioutil.ReadAll(r.Body)

	log.Debugln(string(b))
	var js map[string]interface{}

	err := CheckPodcfg(b, true)
	if err != nil {
		respondError(w, http.StatusBadRequest, "Input Error: "+err.Error())
		return
	}
	deviceid, err := jsonparser.GetString(b, "spec", "nodeSelector", "kubernetes.io/hostname")
	if err != nil || len(deviceid) < 1 {
		respondError(w, http.StatusBadRequest, "wrong kubernetes.io/hostname: "+err.Error())
		return
	}
	name, err := jsonparser.GetString(b, "metadata", "name")
	if err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}
	b, err = jsonparser.Set(b, []byte(`"IfNotPresent"`), "spec", "containers", "[0]", "imagePullPolicy")
	if err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err = json.Unmarshal(b, &js); err != nil {
		respondError(w, http.StatusInternalServerError, "Unexpect Error: "+string(b))
		return
	}

	//create in k8s master which the node is in.
	if _, ok := NodeInKube(deviceid); ok {
		//back assign to Req Body
		r.Body = ioutil.NopCloser(bytes.NewReader(b))

		BackportCreate(w, r)
		return
	}

	b = jsonparser.Delete(b, "spec", "nodeSelector")
	cfg := jsonparser.Delete(b, "spec", "imagePullSecrets")
	log.Debugln(string(cfg))
	timenow := time.Now().Format(time.RFC3339)
	app := Application{
		Appname:  name,
		Deviceid: deviceid,
		//Cfgfactory: b64.StdEncoding.EncodeToString(cfg),
		Cfgfactory: string(cfg),
		Userid:     vars["userid"],
		Status:     PENDING,
		Task:       r.URL.Query().Get("taskid"),
		Message:    "Wait to schedule and launch",
		Createtime: timenow,
		Lastupdate: timenow,
	}

	err = DBcreateApp(app)
	if err != nil {
		if err == AppExist {
			respondError(w, http.StatusConflict, err.Error())
			return
		} else {
			respondError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	log.Infof("Created Application: %s device %s", app.Appname, app.Deviceid)
	go MQcreatApp(app)
	respondJSON(w, http.StatusCreated, AppsToHttp(append([]Application{}, app)))
}

// Create apps of group mode
func GroupCreateAppHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)

	log.Infoln("CreateAppHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)

	userid := vars["userid"]
	groupid := r.URL.Query().Get("groupid")
	taskid := r.URL.Query().Get("taskid")
	if taskid == "" {
		taskid = string(GenrandInt(32))
	}

	if len(groupid) < 1 {
		respondError(w, http.StatusBadRequest, "groupid is requried")
		return
	}

	defer r.Body.Close()
	b, _ := ioutil.ReadAll(r.Body)

	log.Debugln(string(b))
	var js map[string]interface{}

	err := CheckPodcfg(b, false)
	if err != nil {
		respondError(w, http.StatusBadRequest, "Input Error: "+err.Error())
		return
	}
	b, err = jsonparser.Set(b, []byte(`"IfNotPresent"`), "spec", "containers", "[0]", "imagePullPolicy")
	if err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	containerimage, err := jsonparser.GetString(b, "spec", "containers", "[0]", "image")
	registryL := strings.Split(strings.Split(containerimage, `:`)[0], `/`)
	//basename := registryL[len(registryL)-1] + fmt.Sprintf("-%d", rand.Int(20))
	basename := registryL[len(registryL)-1]

	b, err = jsonparser.Set(b, []byte(fmt.Sprintf(`"%s"`, basename)), "metadata", "name")
	if err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	b, err = jsonparser.Set(b, []byte(fmt.Sprintf(`"%s"`, basename)), "spec", "containers", "[0]", "name")
	if err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err = json.Unmarshal(b, &js); err != nil {
		respondError(w, http.StatusInternalServerError, "Unexpect Error: "+string(b))
		return
	}

	b = jsonparser.Delete(b, "spec", "nodeSelector")
	cfg := jsonparser.Delete(b, "spec", "imagePullSecrets")
	log.Debugln(string(cfg))

	T := TaskInfo{
		ID:      taskid,
		Current: 0,
		Userid:  userid,
		Groupid: groupid,
		Appcfg:  string(cfg),
	}

	err = DBGroupInQueue(T)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "Unexpect Error: "+err.Error())
	}
	respondJSON(w, http.StatusOK,
		map[string]interface{}{"code": 0, "id": T.ID})
}

//Delete Task and apps under the task
func GroupDeletHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)

	log.Infoln("GroupDeletHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)

	userid := vars["userid"]
	taskid := vars["taskid"]
	//taskid := r.URL.Query().Get("taskid")
	if taskid == "" {
		respondError(w, http.StatusBadRequest, "taskid is null")
		return
	}
	as, err := DBqueryappbyuser(userid)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if len(as) == 0 {
		respondError(w, http.StatusInternalServerError, "no any apps")
		return
	}
	go func() {
		for _, v := range as {
			if v.Task == taskid {
				err := DelApp(v)
				if err != nil {
					delappch <- v
				}
			}
		}
		_ = DBDelTask(taskid)

	}()
	respondJSON(w, http.StatusOK, map[string]interface{}{"code": 0, "message": "accepted"})
	return

}

func FilterApps(apps []Application, deviceid, userid, taskid, status string) []Application {
	var as []Application
	for _, v := range apps {
		if AppMeetTask(v, taskid) && AppMeetStatus(v, status) &&
			AppMeetDevice(v, deviceid) && AppMeetUser(v, userid) {
			as = append(as, v)
		}
	}
	sort.Sort(Apps(as))
	return as

}

func GetTaskListHandler(w http.ResponseWriter, r *http.Request) {
	log.Infoln("GetTaskListHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)
	vars := mux.Vars(r)
	tasklist, err := DBGetTaskList(vars["userid"])
	if err != nil {
		respondError(w, http.StatusInternalServerError, "Unexpect Error: "+err.Error())
	}
	var names []string
	for _, v := range tasklist {
		names = append(names, v.ID)
	}
	respondJSON(w, http.StatusOK, map[string]interface{}{"code": 0, "items": names})

}

// Get apps instance by user
func GetAppsHandler(w http.ResponseWriter, r *http.Request) {
	var apps []Application
	vars := mux.Vars(r)

	taskid := r.URL.Query().Get("taskid")
	appstatus := r.URL.Query().Get("status")
	device := r.URL.Query().Get("device")

	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	offset, _ := strconv.Atoi(r.URL.Query().Get("offset"))
	if limit <= 0 {
		limit = 50
	}

	userid := vars["userid"]

	log.Infoln("GetAppsHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)
	if device != "" {
		/*
			a := Application{
				Deviceid: device,
			}
			SendMqAction(append([]Application{}, a), ACTSTATUS)
			time.Sleep(1 * time.Second)
		*/
		as, err := DBscanBydeviceid(device)
		if err != nil {
			respondError(w, http.StatusInternalServerError, err.Error())
			return
		}
		apps = FilterApps(as, "", userid, taskid, appstatus)
	} else {
		as, err := DBqueryappbyuser(userid)
		if err != nil {
			respondError(w, http.StatusInternalServerError, err.Error())
			return
		}
		apps = FilterApps(as, device, "", taskid, appstatus)
	}
	//kubeapps, err := BackportGetApps(w, r)
	kubeapps := KubeApps
	for _, v := range kubeapps {
		apps = append(apps, v)
	}
	if limit > 0 {
		var HttpApps RespHttpList
		applength := len(apps)
		if offset+limit < applength {
			HttpApps = AppsToHttp(apps[offset:(offset + limit)])
		} else if offset < applength {
			HttpApps = AppsToHttp(apps[offset:])
		}
		HttpApps.Limit = limit
		HttpApps.Offset = offset
		HttpApps.Total = applength - len(kubeapps)

		respondJSON(w, http.StatusOK, HttpApps)
		return
	}
	respondJSON(w, http.StatusOK, AppsToHttp(apps))
}

// Get Application  Summary
func GetAppSumHandler(w http.ResponseWriter, r *http.Request) {
	var sum []ApplicationSum

	vars := mux.Vars(r)

	log.Infoln("GetAppSumHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)

	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	offset, _ := strconv.Atoi(r.URL.Query().Get("offset"))
	if limit <= 0 {
		limit = 10
	}

	userid := vars["userid"]
	QName := r.URL.Query().Get("appname")
	QDevice := r.URL.Query().Get("device")

	apps, err := DBqueryappbyuser(userid)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	for _, a := range apps {
		slicen := strings.Split(a.Appname, `-`)
		aname := strings.Join(slicen[0:len(slicen)-1], `-`)

		if len(QName) > 2 && QName != aname {
			continue
		}
		if len(QDevice) > 2 && !strings.Contains(a.Deviceid, QDevice) {
			continue
		}

		if k, exist := InAppSums(aname, sum); exist {
			sum[k].Items = append(sum[k].Items, a)
			sum[k].Total += 1
		} else {
			sum = append(sum, ApplicationSum{
				Name:   aname,
				Total:  1,
				Limit:  limit,
				Offset: offset,
				Items:  append([]Application{}, a),
			})
		}

	}
	for k, v := range sum {
		if offset+limit < v.Total {
			sum[k].Items = sum[k].Items[offset:(offset + limit)]
		}
	}
	respondJSON(w, http.StatusOK, sum)

}

// Get Specific Task Summary
func GetTaskSumHandler(w http.ResponseWriter, r *http.Request) {
	var tasksum TaskSum
	var ok bool

	log.Infoln("GetTaskSumHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)
	vars := mux.Vars(r)
	userid := vars["userid"]
	taskid := vars["taskid"]
	//taskid := r.URL.Query().Get("taskid")

	tasksum, ok = CacheGetTaskSum(taskid)
	taskdone := false

	if ok {
		respondJSON(w, http.StatusOK, tasksum)
		return
	} else {
		ts, err := DBGetTask(taskid)
		if err != nil {
			respondError(w, http.StatusInternalServerError, err.Error())
			return
		}
		if len(ts) == 0 {
			respondError(w, http.StatusNotFound, "task is not existed")
			return
		} else {
			tasksum.ID = ts[0].ID
			tasksum.Total = ts[0].Total
			tasksum.Pending = ts[0].Total - ts[0].Current
			//task is done, ok to be cache
			if tasksum.Pending == 0 {
				taskdone = true
			}
		}
		as, err := DBqueryappbyuser(userid)
		if err != nil {
			respondError(w, http.StatusInternalServerError, err.Error())
			return
		}
		for _, v := range as {
			if v.Task == taskid {
				if v.Status == PENDING {
					tasksum.Pending += 1
				} else if v.Status == CREATING {
					tasksum.Creating += 1
				} else if v.Status == FAILED {
					tasksum.Failed += 1
				} else if v.Status == RUNNING {
					tasksum.Running += 1
				}
			}
		}

		if tasksum.Total >= 0 {
			tasksum.Stopped = tasksum.Total -
				tasksum.Pending -
				tasksum.Creating -
				tasksum.Failed -
				tasksum.Running
		}
		if taskdone {
			CacheAddTaskSum(taskid, tasksum, 10*time.Minute)
		} else {
			CacheAddTaskSum(taskid, tasksum, 15*time.Second)
		}
		log.Debugln(tasksum)
		respondJSON(w, http.StatusOK, tasksum)
	}

}

// Get specific app with current user
func GetAppHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)

	log.Infoln("Get Specific AppHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)

	if k, v := PodInKube(vars["appname"]); k {
		respondJSON(w, http.StatusOK, AppsToHttp(append([]Application{}, v)))
		return
	}
	apps, err := DBscanByAppname(vars["appname"], vars["userid"])
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if len(apps) < 1 {
		respondError(w, http.StatusNotFound,
			fmt.Sprintf("app %s not found for user %s", vars["appname"], vars["userid"]))
		return
	}
	respondJSON(w, http.StatusOK, AppsToHttp(apps))
}

// Del app instance
func DelAppHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)

	log.Infoln("DelAppsHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)

	if k, v := PodInKube(vars["appname"]); k {
		BackportDelApp(w, r, v.Appname)
		return
	}
	force := r.URL.Query().Get("force")
	clean := r.URL.Query().Get("clean")

	app, err := DBsetappstatus(vars["appname"], vars["userid"], DELETING)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	app.Status = DELETING
	//sleep for a while to db sync
	time.Sleep(20 * time.Millisecond)

	if len(clean) > 1 {
		err = SendMqAction(append([]Application{}, app), ACTRMIM)
	} else {
		err = MQdeleteApp(app)
	}

	if len(force) > 1 {
		log.Infoln("DleAppsHandler force delete is enabled")
		app.Lastupdate = time.Now().Format(time.RFC3339)
		_ = DBdelItem(app)
		//DBUpdateStatusOnly(app, DELETED)
		respondJSON(w, http.StatusOK, []Application{})
		return
	}
	go func() {
		log.Infoln("TASK started: Force delete after 10 seconds")
		time.Sleep(15 * time.Second)
		app.Lastupdate = time.Now().Format(time.RFC3339)
		_ = DBdelItem(app)
		//DBUpdateStatusOnly(app, DELETED)
	}()
	respondJSON(w, http.StatusOK, AppsToHttp(append([]Application{}, app)))
}

// Restart app instance
func RestartAppHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)

	log.Infoln("RestartAppHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)
	/*
		apps, err := DBscanByAppname(vars["appname"], vars["userid"])
		if err != nil {
			respondError(w, http.StatusInternalServerError, err.Error())
			return
		}
		if len(apps) < 1 {
			respondError(w, http.StatusNotFound,
				fmt.Sprintf("app %s not found for user %s", vars["appname"], vars["userid"]))
			return
		}
	*/
	app, err := DBsetappstatus(vars["appname"], vars["userid"], REBOOTING)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	app.Status = REBOOTING

	_ = MQdeleteApp(app)
	go func() {
		time.Sleep(200 * time.Millisecond)
		_ = MQdeleteApp(app)
	}()

	respondJSON(w, http.StatusOK, AppsToHttp(append([]Application{}, app)))
}

// Get device node info
func GetNodeHandler(w http.ResponseWriter, r *http.Request) {
	log.Infoln("GetNodeHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)
	vars := mux.Vars(r)

	if v, ok := NodeInKube(vars["deviceid"]); ok {
		respondJSON(w, http.StatusOK, v)
		return
	}
	devs, err := DBqueryDevice(vars["deviceid"])
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}

	if len(devs) > 0 {
		var kuben Nodetype
		log.Debugln("GetNodeHandler Load From DB", devs)

		Kaddr := KubeIPaddr{
			Type:    "InternalIP",
			Address: devs[0].IpAddr,
		}

		kuben.Meta.Name = vars["deviceid"]
		kuben.Status.Addresses = append(kuben.Status.Addresses, Kaddr)

		respondJSON(w, http.StatusOK, kuben)
	} else {
		respondJSON(w, http.StatusNotFound,
			map[string]interface{}{"code": http.StatusNotFound, "message": "device not found"})
		return
	}
}

// Flush Caches
func FlushCacheHandler(w http.ResponseWriter, r *http.Request) {
	log.Infoln("FlushCacheHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)

	CacheFlush(mux.Vars(r)["userid"])

	respondJSON(w, http.StatusOK, "ok")
}

// Sync the app status to cloud
func D2CloudSyncHandler(w http.ResponseWriter, r *http.Request) {
	log.Infoln("D2CloudSyncHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)

	vars := mux.Vars(r)
	devid := vars["deviceid"]

	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	offset, _ := strconv.Atoi(r.URL.Query().Get("offset"))
	if limit <= 0 {
		limit = 50
	}

	if devid == "" {
		respondError(w, http.StatusBadRequest, "deviceid is null")
		return
	}
	a := Application{
		Deviceid: devid,
	}
	SendMqAction(append([]Application{}, a), ACTSTATUS)
	time.Sleep(1 * time.Second)

	apps, err := DBscanBydeviceid(devid)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if limit > 0 {
		var HttpApps RespHttpList
		applength := len(apps)
		if offset+limit < applength {
			HttpApps = AppsToHttp(apps[offset:(offset + limit)])
		} else if offset < applength {
			HttpApps = AppsToHttp(apps[offset:])
		}
		HttpApps.Limit = limit
		HttpApps.Offset = offset
		HttpApps.Total = applength

		respondJSON(w, http.StatusOK, HttpApps)
		return
	}
	respondJSON(w, http.StatusOK, AppsToHttp(apps))
}

// Reload Certs
func ReloadCertsHandler(w http.ResponseWriter, r *http.Request) {
	log.Infoln("Reload Certs", r.Method, r.URL.Path, r.RemoteAddr)
	LoadCerts()
	respondJSON(w, http.StatusOK, "ok")
}

// Get app event logs
func GetAppEventLogHandler(w http.ResponseWriter, r *http.Request) {
	log.Infoln("GetAppEventLogHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)
	vars := mux.Vars(r)

	apps, err := DBscanByAppname(vars["appname"], vars["userid"])
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if len(apps) < 1 {
		respondError(w, http.StatusNotFound,
			fmt.Sprintf("app %s not found for user %s", vars["appname"], vars["userid"]))
		return
	}

	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.WriteHeader(200)

	log.Debugln("Get AppLogHandler invoked", r.Method, r.URL.Path)

	fname := vars["appname"] + "_" + vars["userid"]
	f, err := os.Open(applogspath + fname)
	if err != nil {
		log.Errorln("GetLog", err)
		w.Write([]byte(""))
		return
	}
	defer f.Close()
	scanner := bufio.NewScanner(f)

	for scanner.Scan() {
		log.Debugln(scanner.Text())
		//fmt.Println(scanner.Bytes())
		fmt.Fprintln(w, scanner.Text())
		//w.Write(scanner.Bytes())
	}
}

// Get app logs
func GetAppLogsLogHandler(w http.ResponseWriter, r *http.Request) {
	log.Infoln("Get AppLogHandler invoked", r.Method, r.URL.Path, r.RemoteAddr)

	vars := mux.Vars(r)
	apps, err := DBscanByAppname(vars["appname"], vars["userid"])
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if len(apps) < 1 {
		respondError(w, http.StatusNotFound,
			fmt.Sprintf("app %s not found for user %s", vars["appname"], vars["userid"]))
		return
	}

	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.WriteHeader(200)

	fname := vars["appname"] + ".log"
	before := time.Now().Unix()

	log.Debugln("before", before)
	go SendMqAction(apps, ACTPUTLOG)

	for i := 0; i < 5; i++ {
		info, err := os.Stat(applogspath + fname)
		if err == nil {
			if info.ModTime().Unix()-before > 0 {
				break
			} else {
				log.Debugln("File Stat", info.ModTime().Unix())
			}
		}
		time.Sleep(1 * time.Second)
	}
	f, err := os.Open(applogspath + fname)
	if err != nil {
		log.Errorln("GetLog", err)
		w.Write([]byte(" \n"))
		return
	}

	defer f.Close()
	scanner := bufio.NewScanner(f)

	for scanner.Scan() {
		log.Debugln(scanner.Text())
		//fmt.Println(scanner.Bytes())
		fmt.Fprintln(w, scanner.Text())
		//w.Write(scanner.Bytes())
	}
}
