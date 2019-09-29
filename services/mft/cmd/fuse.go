// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"crypto/sha256"
	"crypto/x509"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/jinzhu/gorm/dialects/postgres"
	"github.com/lib/pq"
	"net/http"
)

type FuseConfig struct {
	Model
	Name  string         `gorm:"type:varchar(100);unique_index:fuseconfigname_oemid;not null" json:"name"`
	OemID string         `gorm:"type:varchar(64);unique_index:fuseconfigname_oemid;not null" json:"oem_id"`
	KeyID *uuid.UUID     `gorm:"type:uuid"  json:"key_id"`
	Data  postgres.Jsonb `json:"data"`
}

type FuseConfigData struct {
	Config      string `gorm:"type:varchar(4096);" json:"config"`
	Description string `json:"description"`
}

func FuseConfigCreateHandler(c *gin.Context) {
	type fuseConfigCreate struct {
		Name        string `json:"name"`
		KeyID       string `json:"key_pair_id"`
		Content     string `json:"content"`
		Description string `json:"description"`
	}

	var req fuseConfigCreate
	var key RootKey

	p := make([]byte, 4096)
	i, _ := c.Request.Body.Read(p)
	json.Unmarshal(p[:i], &req)

	db.AutoMigrate(&FuseConfig{})

	var data FuseConfigData
	data.Description = req.Description

	var newFuseConfig = FuseConfig{
		Name:  req.Name,
		OemID: GetOemID(c),
	}

	if keyID, err := uuid.Parse(req.KeyID); err == nil {
		newFuseConfig.KeyID = &keyID
		key.Model.ID = keyID
		db.Model(&RootKey{}).First(&key)
		var rootKey RootKeyData
		json.Unmarshal(key.Data.RawMessage, &rootKey)

		b := []byte(rootKey.Key)
		privPem, _ := pem.Decode(b)
		if privPem == nil {
			c.JSON(500, gin.H{
				"message": "invalid private key",
				"status":  "success",
			})
			return
		}
		switch privPem.Type {
		case "RSA PRIVATE KEY":
			priv, _ := x509.ParsePKCS1PrivateKey(privPem.Bytes)
			pub := priv.PublicKey.N.Bytes()

			keyLen := len(pub)
			keyLenPad := make([]byte, 4)
			binary.LittleEndian.PutUint32(keyLenPad, uint32(keyLen*2))
			data := append(keyLenPad, []byte(pub)...)

			e := make([]byte, len(pub))
			binary.BigEndian.PutUint32(e[len(pub)-4:], uint32(priv.PublicKey.E))
			data = append(data, e...)

			if len(pub)*2 < 0x400 {
				pad := make([]byte, 0x400-len(pub)*2)
				data = append(data, pad...)
			}
			hash := Sha256Sum(data)
			for i := 0; i < 64; i += 8 {
				req.Content = fmt.Sprintf("%s\nSRKH_%d=%s", req.Content, i/8, hash[i:i+8])
			}
		}
	}

	data.Config = req.Content
	d, _ := json.Marshal(&data)
	newFuseConfig.Data = postgres.Jsonb{RawMessage: d}
	if err := db.Create(&newFuseConfig).Error; err != nil {
		c.JSON(http.StatusCreated, gin.H{
			"status": "fail",
			"code":   err.(*pq.Error).Code,
		})
		return
	}

	c.JSON(200, gin.H{
		"message": "create config file successfully",
		"status":  "success",
	})
}

func FuseConfigListHandler(c *gin.Context) {
	type resp struct {
		Id          string `json:"id"`
		CreatedAt   string `json:"create_time"`
		UpdatedAt   string `json:"update_time"`
		Name        string `json:"name"`
		Description string `json:"description"`
		KeyID       string `json:"key_pair_id"`
		KeyPair     string `json:"key_pair"`
	}
	var (
		configs   []resp
		offset    = "0"
		limit     = "10"
		cont      uint64
		order     = "created_at DESC"
		orderType = "DESC"
	)
	if c.Query("offset") != "" {
		offset = c.Query("offset")
	}
	if c.Query("limit") != "" {
		limit = c.Query("limit")
	}
	if c.Query("orderType") != "" {
		switch c.Query("orderType") {
		case "desc":
			orderType = "DESC"
		case "asc":
			orderType = "ASC"
		default:
			orderType = "DESC"
		}
	}

	if c.Query("orderBy") != "" {
		switch c.Query("orderBy") {
		case "create_time":
			order = "created_at" + " " + orderType
		case "update_time":
			order = "updated_at" + " " + orderType
		default:
			order = "created_at" + " " + orderType
		}
	}
	oemID := GetOemID(c)
	db.Model(&FuseConfig{}).
		Where("fuse_configs.name LIKE ?", fmt.Sprintf("%%%s%%", c.Query("filter_text"))).
		Where("oem_id = ?", oemID).
		Count(&cont)
	db.Model(&FuseConfig{}).
		Where("fuse_configs.name LIKE ?", fmt.Sprintf("%%%s%%", c.Query("filter_text"))).
		Order(order, true).Limit(limit).
		Offset(offset).
		Select("fuse_configs.id, fuse_configs.name, fuse_configs.created_at, fuse_configs.key_id, root_keys.name as key_pair, fuse_configs.updated_at, fuse_configs.data->>'description' as description").
		Where("fuse_configs.oem_id = ?", oemID).
		Joins("left join root_keys on fuse_configs.key_id = root_keys.id").
		Scan(&configs)

	c.JSON(200, gin.H{
		"total":  cont,
		"offset": offset,
		"limit":  limit,
		"list":   configs,
	})
}

func FuseConfigDetailHandler(c *gin.Context) {
	type resp struct {
		Name        string `json:"name"`
		Config      string `json:"config"`
		KeyID       string `json:"key_pair_id"`
		Description string `json:"description"`
	}
	var config []resp
	if err := db.Model(&FuseConfig{}).
		Where("id= ?", c.Param("id")).
		Limit(1).
		Select("name, created_at, key_id, data->>'config' as config, data->>'description' as description").
		Scan(&config).Error; err != nil {
		c.JSON(500, gin.H{
			"config": err.Error(),
		})
		return
	}

	c.JSON(200, gin.H{
		"description": config[0].Description,
		"config":      config[0].Config,
		"name":        config[0].Name,
		"rootKey":     config[0].KeyID,
	})

}

func FuseConfigDeleteHandler(c *gin.Context) {
	if err := db.Where("id =?", c.Param("id")).Unscoped().Delete(&FuseConfig{}).Error; err != nil {
		c.JSON(500, gin.H{
			"code":   err.(*pq.Error).Code,
			"status": "fail",
		})
		return
	}
	c.JSON(200, gin.H{
		"message": "delete config file successfully",
		"status":  "success",
	})
}

func FuseConfigUpdateHandler(c *gin.Context) {
	type keyUpdate struct {
		Name        string `json:"name"`
		Description string `json:"description"`
	}
	var req keyUpdate

	p := make([]byte, 1024)
	i, _ := c.Request.Body.Read(p)
	json.Unmarshal(p[:i], &req)

	if err := db.Exec("update fuse_configs set name=$1, data=jsonb_set(data, '{description}', to_jsonb($2::text), true) where id=$3", req.Name, req.Description, c.Param("id")).Error; err != nil {
		c.JSON(500, gin.H{
			"message": err.Error(),
			"status":  "file",
		})
		return
	}
	c.JSON(200, gin.H{
		"message": "fuse config update successfully",
		"status":  "success",
	})
}

func Sha256Sum(b []byte) string {
	h := sha256.New()
	h.Write(b)
	d := h.Sum(nil)
	return hex.EncodeToString(d)
}
