// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"encoding/json"
	"fmt"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"strings"
)

const (
	statusActive      = 0
	statusInactive    = 1
	statusDestructive = 2
	statusNew         = 10
	statusCreated     = 11
	lifeCycleCreated  = 1
	lifeCycleNew      = 2
	lifeCycleAuth     = 3
	lifeCycleActive   = 4
	lifeCycleInactive = 5
	lifeCycleRetired  = 6
)

func SetLifeCycle(status uint, name string) error {
	return esdb.Exec("UPDATE hosts SET lifecycle=? WHERE name=?", status, name).Error
}

func SetMftStatus(id string, status uint) error {
	return db.Exec("UPDATE devices SET status=? where id=? and status != 2", status, id).Error
}

func GetEnrollStatus(id string) (uint, error) {
	var (
		d   Device
		err error
	)
	if d.ID, err = uuid.Parse(id); err != nil {
		return 0, err
	}
	if err = db.Select("id, status").First(&d, &d).Error; err != nil {
		return 0, err
	}
	return d.Status, nil
}

func EnrollDestroyCheckHandler(c *gin.Context) {
	s, _ := GetEnrollStatus(c.Param("id"))
	c.Writer.Write([]byte(string(s)))
}
func EnrollStatusGetHandler(c *gin.Context) {
	var retS string
	s, _ := GetEnrollStatus(c.Param("id"))
	switch s {
	case statusActive:
		retS = "ACTIVE"
	case statusInactive:
		retS = "INACTIVE"
	case statusDestructive:
		retS = "DESTRUCTIVE"
	}
	c.JSON(200, gin.H{
		"status": retS,
	})
}

func EnrollStatusPatchHandler(c *gin.Context) {
	type event struct {
		Status string `json:"status"`
	}
	var (
		req      event
		deviceID string
		retS     string
	)
	p := make([]byte, 1024)
	i, _ := c.Request.Body.Read(p)
	json.Unmarshal(p[:i], &req)

	deviceName := c.Param("id")
	topic := fmt.Sprintf("device/%s", c.Param("id"))
	deviceID = strings.Split(c.Param("id"), ".")[0]
	if s, _ := GetEnrollStatus(deviceID); s == statusDestructive {
		SetLifeCycle(lifeCycleRetired, deviceName)
		c.JSON(200, gin.H{
			"status":  "fail",
			"message": "retired device",
		})
		return
	}

	switch req.Status {
	case "ACTIVE":
		{
			SetMftStatus(deviceID, statusActive)
			SetLifeCycle(lifeCycleActive, deviceName)
		}
	case "INACTIVE":
		{
			SetMftStatus(deviceID, statusInactive)
			SetLifeCycle(lifeCycleInactive, deviceName)
			m := map[string]string{"action": "unenroll"}
			d, _ := json.Marshal(&m)
			if err := SetMftStatus(deviceID, statusInactive); err != nil {
				mqttClient.Publish(topic, 2, false, d)
			}
		}
	case "DESTRUCTIVE":
		{
			SetMftStatus(deviceID, statusDestructive)
			SetLifeCycle(lifeCycleRetired, deviceName)
			m := map[string]string{"action": "factory_reset"}
			d, _ := json.Marshal(&m)
			if err := SetMftStatus(deviceID, statusDestructive); err != nil {
				mqttClient.Publish(topic, 2, false, d)
			}
		}
	}
	s, err := GetEnrollStatus(deviceID)
	if err != nil {
		c.JSON(200, gin.H{
			"status":  "fail",
			"message": err.Error(),
		})
	}
	switch s {
	case statusActive:
		retS = "ACTIVE"
	case statusInactive:
		retS = "INACTIVE"
	case statusDestructive:
		retS = "DESTRUCTIVE"
	}
	c.JSON(200, gin.H{
		"status": retS,
		"rs":     s,
	})
}
