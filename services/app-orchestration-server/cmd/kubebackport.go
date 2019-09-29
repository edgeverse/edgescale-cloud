// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"bytes"
	_ "crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"net/http"
	"time"
)

/*
type RespHttpList struct {
	Code       int        `json:"code`
	ApiVersion string     `json:"apiVersion"`
	Items      []RespHttp `json:"items"`
}
type Resppod struct {
	Meta struct {
		CreationTimestamp string `json:"creationTimestamp"`
		Name              string `json:"name"`
		UID               string `json:"uid"`
		NodeName          string `json:"nodeName"`
	} `json:"metadata"`
	Status struct {
		HostIP    string `json:"hostIP"`
		Phase     string `json:"phase"`
		Message   string `json:"message"`
		Reason    string `json:"reason"`
		StartTime string `json:"startTime"`
	} `json:"status"`
}
*/

type NodeItems struct {
	Code       int        `json:"code"`
	ApiVersion string     `json:"apiVersion"`
	Kind       string     `json:"kind"`
	Items      []Nodetype `json:"items,omitempty"`
	Message    string     `json:"message"`
	//Node       Nodetype   `json:"metadata,omitempty"`
}

type Nodetype struct {
	Meta struct {
		Name string `json:"name"`
	} `json:"metadata"`

	Status struct {
		Addresses []KubeIPaddr `json:"addresses"`
	} `json:"status"`
}

type KubeIPaddr struct {
	Type    string `json:"type"`
	Address string `json:"address"`
}

type PodItems struct {
	Code       int       `json:"code"`
	ApiVersion string    `json:"apiVersion"`
	Kind       string    `json:"kind"`
	Items      []Podtype `json:"items"`
	Message    string    `json:"message"`
}

type Podtype struct {
	Meta   Podmeta   `json:"metadata"`
	Spec   Podspec   `json:"spec"`
	Status Podstatus `json:"status"`
}

type Poderror struct {
	Code       int     `json:"code"`
	ApiVersion string  `json:"apiVersion"`
	Kind       string  `json:"kind"`
	Meta       Podmeta `json:"metadata"`
	Spec       Podspec `json:"spec"`
	Status     string  `json:"status"`
	Message    string  `json:"message"`
}

type Podmeta struct {
	CreationTimestamp string `json:"creationTimestamp"`
	Labels            struct {
		Name string `json:"name"`
	} `json:"labels"`
	Name            string `json:"name"`
	Namespace       string `json:"namespace"`
	ResourceVersion string `json:"resourceVersion"`
	SelfLink        string `json:"selfLink"`
	UID             string `json:"uid"`
}

type Podspec struct {
	Containers       []SpecContainers `json:"containers"`
	DNSPolicy        string           `json:"dnsPolicy"`
	HostNetwork      bool             `json:"hostNetwork"`
	ImagePullSecrets []struct {
		Name string `json:"name"`
	} `json:"imagePullSecrets"`
	NodeName     string `json:"nodeName"`
	NodeSelector struct {
		KubernetesIoHostname string `json:"kubernetes.io/hostname"`
	} `json:"nodeSelector"`
	RestartPolicy   string `json:"restartPolicy"`
	SchedulerName   string `json:"schedulerName"`
	SecurityContext struct {
	} `json:"securityContext"`
	ServiceAccount                string `json:"serviceAccount"`
	ServiceAccountName            string `json:"serviceAccountName"`
	TerminationGracePeriodSeconds int    `json:"terminationGracePeriodSeconds"`
	Volumes                       []struct {
		Name   string `json:"name"`
		Secret struct {
			DefaultMode int    `json:"defaultMode"`
			SecretName  string `json:"secretName"`
		} `json:"secret"`
	} `json:"volumes"`
}

type Podstatus struct {
	Conditions        []Stconditions        `json:"conditions"`
	ContainerStatuses []StcontainerStatuses "containerStatuses"
	HostIP            string                `json:"hostIP"`
	Phase             string                `json:"phase"`
	PodIP             string                `json:"podIP"`
	QosClass          string                `json:"qosClass"`
	StartTime         string                `json:"startTime"`
}

type Stconditions struct {
	LastProbeTime      interface{} `json:"lastProbeTime"`
	LastTransitionTime string      `json:"lastTransitionTime"`
	Status             string      `json:"status"`
	Type               string      `json:"type"`
	Message            string      `json:"message"`
	Reason             string      `json:"reason"`
}

type StcontainerStatuses struct {
	ContainerID string `json:"containerID"`
	Image       string `json:"image"`
	ImageID     string `json:"imageID"`
	LastState   struct {
		Terminated struct {
			ContainerID string `json:"containerID"`
			ExitCode    int    `json:"exitCode"`
			FinishedAt  string `json:"finishedAt"`
			Reason      string `json:"reason"`
			StartedAt   string `json:"startedAt"`
		} `json:"terminateda"`
	} `json:"lastState"`
	Name         string `json:"name"`
	Ready        bool   `json:"ready"`
	RestartCount int    `json:"restartCount"`
	State        struct {
		Waiting struct {
			Message string `json:"message"`
			Reason  string `json:"reason"`
		} `json:"waiting"`
		Running struct {
			StartedAt string `json:"startedAt"`
		} `json:"running"`
	} `json:"state"`
}

type SpecContainers struct {
	Args            []string `json:"args"`
	Command         []string `json:"command"`
	Image           string   `json:"image"`
	ImagePullPolicy string   `json:"imagePullPolicy"`
	Name            string   `json:"name"`
	Resources       struct {
	} `json:"resources"`
	SecurityContext struct {
		Privileged bool `json:"privileged"`
	} `json:"securityContext"`
	TerminationMessagePath   string `json:"terminationMessagePath"`
	TerminationMessagePolicy string `json:"terminationMessagePolicy"`
	VolumeMounts             []struct {
		MountPath string `json:"mountPath"`
		Name      string `json:"name"`
		ReadOnly  bool   `json:"readOnly"`
	} `json:"volumeMounts"`
}

var KubeApps []Application

func SendHttpRequest(argUrl string, argReq []byte, argType string) ([]byte, error) {
	/*
		fmt.Print(">============<\n")
		fmt.Printf("[request url]:%v\n", argUrl)
		fmt.Printf("[request content]:%v\n", argReq)
		fmt.Printf("[request type]:%v\n", argType)
		fmt.Printf("[request head]:%+v\n", argHead)
	*/
	req, err := http.NewRequest(argType, argUrl, bytes.NewBuffer(argReq))
	if err != nil {
		return nil, err
	}
	req.Header.Add("User-Agent", "kubectl/v1.7.0")
	req.Header.Add("Accept", "application/json")
	tr := &http.Transport{
		//TLSClientConfig:       &tls.Config{InsecureSkipVerify: true},
		ResponseHeaderTimeout: time.Second * 15,
		DisableKeepAlives:     true,
	}
	client := &http.Client{Transport: tr}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, _ := ioutil.ReadAll(resp.Body)
	return body, nil
}

func Dohttp(r *http.Request) ([]byte, error) {

	urlv := "http://" + *kubeaddr + r.URL.Path
	if r.URL.RawQuery != "" {
		urlv = urlv + "?" + r.URL.RawQuery
	}

	method := r.Method
	body, _ := ioutil.ReadAll(r.Body)

	log.Debugln(r.RemoteAddr, method, urlv)
	//log.Debugln("body: ", string(body))

	defer r.Body.Close()
	return SendHttpRequest(urlv, body, method)
}

func Podwrap(pods []byte) (RespHttpList, error) {

	//fmt.Println(string(resp))

	poditem := PodItems{}
	wraps := RespHttpList{}

	if err := json.Unmarshal(pods, &poditem); err != nil {
		fmt.Println("items error", string(pods))
		//return nil, err
	}

	//error message
	if poditem.Code != 0 {
		log.Errorln("Error: ", poditem)
		return wraps, errors.New(poditem.Message)
	}

	//single pod message
	if len(poditem.Items) == 0 {
		log.Debugln("k8s getting signle pod")
		podv := Podtype{}
		if err := json.Unmarshal(pods, &podv); err != nil {
			fmt.Println("To pod struction error", string(pods))
			return wraps, err
		}
		poditem.Items = append(poditem.Items, podv)
	}

	log.Debugln("k8s process pods list")
	//podlist message
	wraps.ApiVersion = "v1"
	wraps.Code = 0
	for _, pod := range poditem.Items {
		if pod.Meta.Name == "" {
			continue
		}
		pwrap := RespHttp{}
		pwrap.Meta.CreationTimestamp = pod.Meta.CreationTimestamp
		pwrap.Meta.Name = pod.Meta.Name
		pwrap.Meta.NodeName = pod.Spec.NodeName
		if pod.Spec.NodeName == "" {
			pwrap.Meta.NodeName = pod.Spec.NodeSelector.KubernetesIoHostname
		}
		pwrap.Meta.UID = pod.Meta.UID

		pwrap.Status.HostIP = pod.Status.HostIP
		pwrap.Status.StartTime = pod.Status.StartTime
		pwrap.Status.Phase = "Creating"
		pwrap.Status.Message = ""
		if len(pod.Status.ContainerStatuses) > 0 {
			if pod.Status.ContainerStatuses[0].State.Waiting.Reason != "" {
				pwrap.Status.Phase = "Waiting"
				pwrap.Status.Reason = pod.Status.ContainerStatuses[0].State.Waiting.Reason
				pwrap.Status.Message = pod.Status.ContainerStatuses[0].State.Waiting.Message
				if len(pwrap.Status.Message) < 2 {
					pwrap.Status.Message = "containers with unready status, image downloading"
				}
			} else if startat := pod.Status.ContainerStatuses[0].State.Running.StartedAt; startat != "" {
				pwrap.Status.Phase = "Running"
				pwrap.Status.Message = "Started At:" + startat
			}
		} else if pod.Status.Phase == "Pending" {
			pwrap.Status.Phase = "pending"
			pwrap.Status.Reason = ""
			if len(pod.Status.Conditions) == 0 {
				pwrap.Status.Message = ""
			} else {
				pwrap.Status.Message = pod.Status.Conditions[0].Message
				pwrap.Status.Reason = pod.Status.Conditions[0].Reason
			}
		}
		wraps.Items = append(wraps.Items, pwrap)
	}
	return wraps, nil
}

func NodeInKube(name string) (Nodetype, bool) {

	if len(name) < 10 || *kubeaddr == "" {
		return Nodetype{}, false
	}
	//out, _ := exec.Command("bash", "-c", `kubectl get node|awk '{print $1}'`).Output()
	//nlist := strings.Split(string(out), "\n")

	urlv := "http://" + *kubeaddr + "/api/v1/nodes"
	if resp, err := SendHttpRequest(urlv, nil, "GET"); err == nil {
		var nodes NodeItems
		if err = json.Unmarshal(resp, &nodes); err == nil {
			for _, v := range nodes.Items {
				if v.Meta.Name == name {
					log.Debugf("node %s in k8s cluster", name)
					return v, true
				}
			}
		} else {
			log.Errorln(err)
		}
	}
	return Nodetype{}, false
}

func PodInKube(name string) (bool, Application) {

	if len(name) < 10 || *kubeaddr == "" {
		return false, Application{}
	}

	for _, v := range KubeApps {
		if name == v.Appname {
			return true, v
		}
	}
	return false, Application{}
	/*
		urlv := "http://" + *kubeaddr + "/api/v1/namespaces/default/pods"

		if resp, err := SendHttpRequest(urlv, nil, "GET"); err == nil {
			if poditems, err := Podwrap(resp); err == nil {
				for _, v := range poditems.Items {
					if v.Meta.Name == name {
						return true
					}
				}
			}
		}
		return false
	*/
}

func KubeListen() {
	if *kubeaddr == "" {
		return
	}
	go func() {
		r, _ := http.NewRequest("GET", "http://127.0.0.1", bytes.NewBuffer(nil))
		for {
			KubeApps, _ = BackportGetApps(nil, r)
			time.Sleep(2 * time.Second)
		}
	}()
}

func BackportPod(w http.ResponseWriter, r *http.Request, name string) (RespHttpList, error) {

	r.URL.Path = "/api/v1/namespaces/default/pods"
	if len(name) > 1 {
		r.URL.Path = r.URL.Path + "/" + name
	}

	resp, err := Dohttp(r)
	if err != nil {
		return RespHttpList{}, err
	}

	return Podwrap(resp)
}

func BackportCreate(w http.ResponseWriter, r *http.Request) {

	log.Warnln("BackportCreate", r.Method, r.URL.Path)
	w.Header().Set("Content-Type", "application/json")

	poditems, err := BackportPod(w, r, "")
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	resp, _ := json.Marshal(poditems)
	w.Write(resp)
}

func BackportGetApp(w http.ResponseWriter, r *http.Request, name string) Application {

	log.Warnln("BackportGetApp", r.Method, r.URL.Path, name)

	for _, v := range KubeApps {
		if name == v.Appname {
			return v
		}
	}
	return Application{}
	/*
		poditems, err := BackportPod(w, r, name)

		w.Header().Set("Content-Type", "application/json")
		if err != nil {
			respondError(w, http.StatusInternalServerError, err.Error())
			return
		}
		resp, _ := json.Marshal(poditems)
		w.Write(resp)
	*/
}

func BackportGetApps(w http.ResponseWriter, r *http.Request) ([]Application, error) {

	var apps []Application
	var app Application

	if *kubeaddr == "" {
		return apps, nil
	}
	log.Debugln("BackportGetApps", r.Method, r.URL.Path)
	poditems, err := BackportPod(w, r, "")
	if err == nil {
		for _, v := range poditems.Items {
			app.Appname = v.Meta.Name
			app.Createtime = v.Meta.CreationTimestamp
			app.Deviceid = v.Meta.NodeName
			app.Status = v.Status.Phase
			app.Message = v.Status.Message
			app.Reason = v.Status.Reason
			apps = append(apps, app)
		}
	}
	return apps, err
}

func BackportDelApp(w http.ResponseWriter, r *http.Request, name string) {

	log.Warnln("BackportDelApp", r.Method, r.URL.Path, name)
	poditems, err := BackportPod(w, r, name)

	w.Header().Set("Content-Type", "application/json")
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	resp, _ := json.Marshal(poditems)
	w.Write(resp)
}
