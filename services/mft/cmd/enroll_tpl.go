// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"fmt"
	"github.com/gin-gonic/gin"
	"reflect"
)

func GetEnrollEndpoints(c *gin.Context, d Device, e interface{}) {

	var trustChain = esconf.Trustchain
	var caURI = esconf.ESTAPI
	var apiURI = esconf.EAPI
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
