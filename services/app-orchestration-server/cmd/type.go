// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"database/sql/driver"
	"encoding/json"
	"errors"
	"time"

	"github.com/google/uuid"
)

const (
	ACTCREATE = "create"
	ACTDELETE = "delete"
	ACTSYNC   = "sync"
	ACTSTATUS = "status"
	ACTPUTLOG = "putlog"
	ACTRMIM   = "rmim"

	PENDING_I   = 0
	CREATING_I  = 1
	STARTING_I  = 2
	RUNNING_I   = 3
	DELETING_I  = 4
	REBOOTING_I = 5
	FAILED_I    = 6
	DELETED_I   = 9

	PENDING   = "pending"
	CREATING  = "creating"
	STARTING  = "starting"
	RUNNING   = "running"
	FAILED    = "failed"
	DELETING  = "deleting"
	REBOOTING = "rebooting"
	DELETED   = "deleted"

	TIMEFORM   = "2006-01-02 15:04:05"
	APIVERSION = "v1"
)

// Kubelet container type
type Container struct {
	Image string `json:"image"`
	Name  string `json:"name"`
}

// Kubelet metadata/annotations type
type Annotation struct {
	Configseen time.Time `json:"kubernetes.io/config.seen"`
	Confighash string    `json:"kubernetes.io/config.hash"`
}

// Kubelet Pod type
type Pod struct {
	Metadata struct {
		Annotations       Annotation `json:"annotations"`
		CreationTimestamp time.Time  `json:"creationTimestamp"`
		Name              string     `json:"name"`
		Namespace         string     `json:"namespace"`
		UID               string     `json:"uid"`
	} `json:"metadata"`
	Spec struct {
		Nodename    string      `json:"nodename"`
		Containers  []Container `json:"containers"`
		Hostnetwork bool        `json:"hostNetwork"`
	} `json:"spec"`
	Status struct {
		Phase   string `json:"phase"`
		HostIP  string `json:"hostIP"`
		Message string `json:"message"`
	} `json:"status"`
}

// Kubelet Podlist type
type Podlist struct {
	Items []Pod `json:"items"`
}

type TaskSum struct {
	ID       string `json:"id"`
	Total    int    `json:"total"`
	Pending  int    `json:"pending"`
	Creating int    `json:"creating"`
	Failed   int    `json:"failed"`
	Running  int    `json:"running"`
	Stopped  int    `json:"stopped"`
}

type TaskInfo struct {
	ID      string `json:"id,omitempty"`
	Current int    `json:"cur,omitempty"`
	Total   int    `json:"ttotal,omitempty"`
	Userid  string `json:"uid,omitempty"`
	Groupid string `json:"gid,omitempty"`
	Appcfg  string `json:"appcfg,omitempty"`
}

type ApplicationSum struct {
	Name   string        `json:"name"`
	Total  int           `json:"total"`
	Limit  int           `json:"limit"`
	Offset int           `json:"offset"`
	Items  []Application `json:"items"`
}

type Mqkubecmd struct {
	// type add/delete/ a pod, sync pods list
	// for upload Type is status
	//"create, delete, sync, status"
	Type       string `json:"type"`
	DeviceId   string `json:"deviceid"`
	Podname    string `json:"podname,omitempty"`
	Podstatus  string `json:"podstatus,omitempty"`
	Podmessage string `json:"podmessage,omitempty"`
	Body       string `json:"body,omitempty"`
}

type MqcmdL struct {
	// type add/delete/ a pod, sync pods list
	// for upload Type is status
	//"create, delete, sync, status"
	Type  string      `json:"type"`
	Items []Mqkubecmd `json:"items"`
}

type Application struct {
	Appname    string `gorm:"column:appname;primary_key" json:"appname"`
	Deviceid   string `gorm:"column:deviceid;primary_key" json:"deviceid"`
	Userid     string `gorm:"column:userid" json:"userid,omitempty"`
	Cfgfactory string `gorm:"column:cfgfactory" json:"cfgfactory,omitempty"`
	Status     string `gorm:"column:appstatus" json:"appstatus,omitempty"`
	Message    string `gorm:"column:appmessage" json:"appmessage,omitempty"`
	Task       string `gorm:"column:task" json:"task,omitempty"`
	Createtime string `gorm:"column:appcreatetime" json:"appcreatetime,omitempty"`
	Lastupdate string `gorm:"column:lastupdate" json:"lastupdate,omitempty"`
	Reason     string `gorm:"column:reason" json:"reason,omitempty"`
}

func (app *Application) String() string {
	bytes, err := json.Marshal(&app)
	if err != nil {
		return err.Error()
	}
	return string(bytes)
}

func (app *Application) TableName() string {
	return "edgescale_app"
}

type Model struct {
	ID        uint      `gorm:"primary_key" json:"id"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type Host struct {
	Model
	Name        string    `json:"name"`
	LastReport  time.Time `json:"last_report"`
	OwnerId     uint      `json:"owner_id"`
	CertTime    string    `json:"cert_time"`
	DccaModelId uint      `json:"dcca_model_id"`
	DisplayName string    `json:"display_name"`
	CustomerId  uuid.UUID `json:"customer_id"`
	SolutionId  uint      `json:"solution_id"`
	Online      bool      `json:"online"`
}

func (h *Host) TableName() string {
	return "hosts"
}

type Apps []Application

type RespHttp struct {
	Meta struct {
		CreationTimestamp string `json:"creationTimestamp"`
		Name              string `json:"name"`
		UID               string `json:"uid,omitempty"`
		NodeName          string `json:"nodename"`
	} `json:"metadata"`
	Status struct {
		HostIP    string `json:"hostIP"`
		Phase     string `json:"phase"`
		Message   string `json:"message"`
		Reason    string `json:"reason"`
		StartTime string `json:"startTime"`
	} `json:"status"`
}

type RespHttpList struct {
	Code       int        `json:"code"`
	ApiVersion string     `json:"apiVersion"`
	Limit      int        `json:"limit,omitempty"`
	Offset     int        `json:"offset"`
	Total      int        `json:"total,omitempty"`
	Items      []RespHttp `json:"items"`
}

type DeviceInfo struct {
	Deviceid   string `json:"device_id"`
	DiskU      string `json:"disk_used"`
	DiskF      string `json:"disk_free"`
	LastReport string `json:"last_report"`
	CpuUsage   string `json:"cpu_usage"`
	MemUsage   string `json:"mem_usage"`
	AppNum     string `json:"app_num"`
	EsVersion  string `json:"es_version"`
	IpAddr     string `json:"ip_address"`
}

type ConfigSetting struct {
	DATABASE           string   `json:"DATABASE"`
	DBHOST             string   `json:"DB_HOST"`
	DBPORT             string   `json:"DB_PORT"`
	DEBUG              bool     `json:"DEBUG"`
	Developers         []string `json:"developers"`
	DEVICESTATUSTABLE  string   `json:"DEVICE_STATUS_TABLE"`
	ENROLLDEVICETABLE  string   `json:"ENROLL_DEVICE_TABLE"`
	FOREMANBASEURL     string   `json:"FOREMAN_BASE_URL"`
	HARBORADMINPASS    string   `json:"HARBOR_ADMIN_PASS"`
	HOSTSITE           string   `json:"HOST_SITE"`
	K8SPORT            string   `json:"APPSERVER_PORT"`
	K8SPORTDEV         string   `json:"APPSERVER_PORT_DEV"`
	K8SPRIVATEHOST     string   `json:"K8S_PRIVATE_HOST"`
	K8SPUBLICHOST      string   `json:"K8S_PUBLIC_HOST"`
	K8SPUBLICHOSTDEV   string   `json:"K8S_PUBLIC_HOST_DEV"`
	LOGURL             string   `json:"LOG_URL"`
	MONGOURI           string   `json:"MONGO_URI"`
	MQTTHOST           string   `json:"MQTT_HOST"`
	MQTTLOCALHOST      string   `json:"MQTT_LOCAL_HOST"`
	MQTTMGMTPASS       string   `json:"MQTT_MGMT_PASSWD"`
	MQTTMGMTUSER       string   `json:"MQTT_MGMT_USER"`
	PASSWORD           string   `json:"PASSWORD"`
	REDISHOST          string   `json:"REDIS_HOST"`
	REDISPORT          string   `json:"REDIS_PORT"`
	REDISPWD           string   `json:"REDIS_PASSWD"`
	REDISDB            int      `json:"REDIS_DB"`
	RESTAPIID          string   `json:"REST_API_ID"`
	RESTAPISHORTID     string   `json:"REST_API_SHORT_ID"`
	SERVICECIPHERSUITE []string `json:"SERVICE_CIPHER_SUITE"`
	SERVICEPROTOCAL    []string `json:"SERVICE_PROTOCAL"`
	USER               string   `json:"USER"`
}

type EdgeText struct {
	Settings ConfigSetting `json:"settings"`
}

type EdgeConfig struct {
	Text EdgeText `json:"text"`
}

func (c *EdgeText) Value() (driver.Value, error) {
	return json.Marshal(*c)
}

func (c *EdgeText) Scan(value interface{}) error {
	if b, ok := value.([]byte); ok {
		return json.Unmarshal(b, c)
	}
	return errors.New("type assertion to []byte failed")
}
