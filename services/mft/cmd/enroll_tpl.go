// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"fmt"
	"github.com/gin-gonic/gin"
	"reflect"
)

func GetEnrollEndpoints(c *gin.Context, d Device, e interface{}) {
	var trustChain = `LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUN2RENDQWlXZ0F3SUJBZ0lVVDN5UWFlQ0lFVjc2NEd4V2xjZytuazZiY1hJd0RRWUpLb1pJaHZjTkFRRUwKQlFBd2NERUxNQWtHQTFVRUJoTUNRMDR4RURBT0JnTlZCQWdNQjJKbGFXcHBibWN4RURBT0JnTlZCQWNNQjJKbAphV3BwYm1jeEVEQU9CZ05WQkFvTUIySmxhV3BwYm1jeEVEQU9CZ05WQkFzTUIySmxhV3BwYm1jeEdUQVhCZ05WCkJBTU1FQ291WldSblpYTmpZV3hsTG1SbGJXOHdIaGNOTVRreE1ETXhNREl3T0RJNFdoY05Namt4TURJNE1ESXcKT0RJNFdqQndNUXN3Q1FZRFZRUUdFd0pEVGpFUU1BNEdBMVVFQ0F3SFltVnBhbWx1WnpFUU1BNEdBMVVFQnd3SApZbVZwYW1sdVp6RVFNQTRHQTFVRUNnd0hZbVZwYW1sdVp6RVFNQTRHQTFVRUN3d0hZbVZwYW1sdVp6RVpNQmNHCkExVUVBd3dRS2k1bFpHZGxjMk5oYkdVdVpHVnRiekNCbnpBTkJna3Foa2lHOXcwQkFRRUZBQU9CalFBd2dZa0MKZ1lFQXRuQkNsc2dKeVp6OGZvTEtZakdza2xhZCtQN0M5RzFISVFKOFhiYnVBZzVaZkk2bDBKa2ZUaHg3TmZRTQpSbTdTdHBYSGRmbER3UFVGOUF5UllYdmJZUE9tb0VuWjVxZUJvdmtWSFZpVVVoSjRhcmo0aGFnRSt3Q0JYTGlkCkcva1BVNVR1TE10Rzd1MUpQZWFVMDdGZTVHditnZ2k5MWw1K2dzUTAzVmFvZVc4Q0F3RUFBYU5UTUZFd0hRWUQKVlIwT0JCWUVGR2dPeCsrVXlQNU80d1A1OEVlTURqT05pd1dqTUI4R0ExVWRJd1FZTUJhQUZHZ094KytVeVA1Two0d1A1OEVlTURqT05pd1dqTUE4R0ExVWRFd0VCL3dRRk1BTUJBZjh3RFFZSktvWklodmNOQVFFTEJRQURnWUVBCk9QYjBYMUM1SXV0Y2dmdkxvWFJvbTZNcmxzcDJERUtxQldZNmtpd0p6U0NGQnVIL01rWWthcCs2ZVdXVFBQOHUKa0UxcHhDL2t2Q2JjQVJkN0g5eUVPYStQS1F3SE0rNnhxTkk2RmswN0x2cnM5bWMwQUlSOTQzV1RxZUk3USsyTQpPNFpZaG5GZDA0eS9pOWdndkhMKy9HWm0vWElXZlJrVmJHbGhQNEtUOC9jPQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg==`

	var caURI = "https://int.e-est.edgescale.demo"
	var apiURI = "https://api.edgescale.demo/v1"
	type deviceModel struct {
		Model   string `json:"model"`
		OwnerID string `json:"owner_id"`
	}

	var model deviceModel
	//esdb.Model(&DccaModels{}).
	esdb.Table("dcca_models").
		Select("concat(model, '.' , type, '.' , platform, '.' , vendor) as model, owner_id").
		Where("id=?", d.ModelID).
		First(&model)

	type DccaCommonService struct {
		Name string `json:"name"`
		URL  string `json:"url"`
		Port string `json:"port"`
	}
	var services []DccaCommonService
	if err := esdb.Table("dcca_common_services").
		Where("user_id= ?", model.OwnerID).
		Select("name, url, port").
		Scan(&services).Error; err != nil {
		fmt.Println(err)
	}

	for _, service := range services {
		switch service.Name {
		case "RestAPI Service":
			apiURI = service.URL
		case "Enrollment Service":
			caURI = service.URL
		}
	}

	reflect.ValueOf(e).Elem().FieldByName("CaUri").SetString(caURI)
	reflect.ValueOf(e).Elem().FieldByName("ApiUri").SetString(apiURI)
	reflect.ValueOf(e).Elem().FieldByName("TrustChain").SetString(trustChain)
	reflect.ValueOf(e).Elem().FieldByName("Model").SetString(model.Model)
}
