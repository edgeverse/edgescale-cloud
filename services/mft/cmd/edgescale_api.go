// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"github.com/gin-gonic/gin"
)

type Hosts struct {
	ID          uint   `json:"id"`
	Name        string `json:"name"`
	LastReport  string `json:"last_report"`
	UpdatedAt   string `json:"update_at"`
	CreatedAt   string `json:"create_at"`
	OwnerId     string `json:"owner_id"`
	Certname    string `json:"certname"`
	DccaModelId uint   `json:"dcca_model_id"`
	DisplayName string `json:"display_name"`
	CustomerId  string `json:"customer_id"`
	SolutionId  uint   `json:"solution_id"`
	Online      bool   `json:"online"`
}

type DccaModels struct {
	ID                uint   `json:"id"`
	Model             string `json:"model"`
	Type              string `json:"type"`
	Platform          string `json:"platform"`
	Vendor            string `json:"vendor"`
	Comment           string `json:"comment"`
	IsPublic          bool   `json:"is_public"`
	OwnerId           uint   `json:"owner_id"`
	defaultSolutionId uint   `json:"default_solution_id"`
}

func CustomerDeviceListHandler(c *gin.Context) {
	type model struct {
		Model    string `json:"model"`
		Type     string `json:"type"`
		Platform string `json:"platform"`
		Vendor   string `json:"vendor"`
	}
	type host struct {
		ID          uint   `json:"id"`
		Name        string `json:"name"`
		LastReport  string `json:"last_report"`
		CreatedAt   string `json:"create_at"`
		Certname    string `json:"certname"`
		DisplayName string `json:"display_name"`
		Online      bool   `json:"online"`
		Model       model  `gorm:"embedded" json:"mode"`
	}
	var (
		hosts     []host
		count     uint = 0
		limit          = "10"
		offset         = "0"
		order          = "created_at DESC"
		orderType      = "DESC"
	)

	cid := c.Param("id")
	uid := GetUserID(c)

	if c.Query("offset") != "" {
		offset = c.Query("offset")
	}
	if c.Query("limit") != "" {
		limit = c.Query("limit")
	}
	if c.Query("order_type") != "" {
		orderType = c.Query("order_type")
	}
	if c.Query("order_by") != "" {
		order = c.Query("order_by") + " " + orderType
	}

	esdb.Model(&Hosts{}).Where("hosts.customer_id = ? AND hosts.owner_id = ?", cid, uid).Count(&count)

	esdb.Model(&Hosts{}).
		Where("hosts.customer_id = ? AND hosts.owner_id = ?", cid, uid).
		Order(order, true).Limit(limit).
		Offset(offset).
		Joins("left join dcca_models on hosts.dcca_model_id = dcca_models.id").
		Select("hosts.name as name, hosts.id as id, hosts.display_name as display_name, dcca_models.type as type, dcca_models.model as model, dcca_models.platform as platform, dcca_models.vendor as vendor").
		Scan(&hosts)
	c.JSON(200, gin.H{
		"total":   count,
		"results": hosts,
		"offset":  offset,
		"limit":   limit,
	})

}
