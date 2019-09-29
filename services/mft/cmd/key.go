// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"crypto"
	"crypto/hmac"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha1"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/jinzhu/gorm/dialects/postgres"
	"github.com/lib/pq"
	"strconv"
	//"github.com/x-pkg/requests"
	//"gopkg.in/yaml.v2"
	//"math/big"
	"net/http"
	//"strings"
	//"time"
)

type RootKey struct {
	Model
	Name    string         `gorm:"type:varchar(100);unique_index:idx_rootkeyname_oemid;not null" json:"name"`
	OemID   string         `gorm:"type:varchar(64);unique_index:idx_oemid_keyhash,idx_rootkeyname_oemid;not null" json:"oem_id"`
	KeyHash string         `gorm:"type:varchar(64);unique_index:idx_oemid_keyhash;not null" json:"key_hash"`
	Data    postgres.Jsonb `json:"data"`
}

type RootKeyData struct {
	Key         string `json:"key"`
	Description string `json:"description"`
	Token       string `json:"token"`
}

func Sha1Sum(b []byte) string {
	h := sha1.New()
	h.Write(b)
	d := h.Sum(nil)
	return hex.EncodeToString(d)
}

func HashFp(h string) string {
	fp := ""
	for i := 0; i < len(h); i++ {
		fp += fmt.Sprintf("%s", string(h[i]))
		if (i+1)%2 == 0 && i < len(h)-1 {
			fp += ":"
		}
	}
	return fp
}

func RootKeyCreateHandler(c *gin.Context) {
	type keyCreate struct {
		Name        string `json:"name"`
		KeyValue    string `json:"key_value"`
		KeyStrength string `json:"key_strength"`
		KeyAlgo     uint   `json:"key_algo"`
		Id          string `json:"id"`
		Description string `json:"description"`
	}

	var req keyCreate

	p := make([]byte, 9212)
	i, _ := c.Request.Body.Read(p)
	json.Unmarshal(p[:i], &req)
	var (
		privPem []byte
		keyHash string
	)

	if req.KeyValue != "" {
		privPem = []byte(req.KeyValue)
		p, _ := pem.Decode(privPem)
		if p == nil {
			c.JSON(500, gin.H{
				"message": "invalid private key",
				"status":  "success",
			})
			return
		}
		switch p.Type {
		case "RSA PRIVATE KEY":
			priv, err := x509.ParsePKCS1PrivateKey(p.Bytes)
			if err != nil {
				c.JSON(500, gin.H{
					"message": err.Error(),
					"status":  "success",
				})
			}
			if err := priv.Validate(); err != nil {
				c.JSON(500, gin.H{
					"message": err.Error(),
					"status":  "success",
				})
				return
			}
			keyHash = Sha1Sum(priv.PublicKey.N.Bytes())
		default:
			c.JSON(500, gin.H{
				"message": "unsupported key type",
				"status":  "success",
			})
			return

		}
	} else {
		bits, err := strconv.Atoi(req.KeyStrength)
		priv, err := rsa.GenerateKey(rand.Reader, bits)
		if err != nil {

			c.JSON(500, gin.H{
				"message": "create config file successfully",
				"status":  "success",
				"error":   err.Error(),
			})
			return
		}
		keyHash = Sha1Sum(priv.PublicKey.N.Bytes())
		block := pem.Block{
			Type:  "RSA PRIVATE KEY",
			Bytes: x509.MarshalPKCS1PrivateKey(priv),
		}
		privPem = pem.EncodeToMemory(&block)
	}

	db.AutoMigrate(&RootKey{})

	var data RootKeyData
	data.Description = req.Description
	data.Key = string(privPem)

	d, _ := json.Marshal(&data)

	var newKey = RootKey{
		Name:    req.Name,
		OemID:   GetOemID(c),
		KeyHash: keyHash,
		Data:    postgres.Jsonb{RawMessage: d},
	}

	if err := db.Create(&newKey).Error; err != nil {
		c.JSON(http.StatusCreated, gin.H{
			"message": "duplicate key name/hash",
			"status":  "fail",
			"key":     string(privPem),
			"code":    err.(*pq.Error).Code,
			"err":     err.Error(),
		})
		return
	}

	c.JSON(200, gin.H{
		"message": "create config file successfully",
		"status":  "success",
		"key":     string(privPem),
		"keyFp":   HashFp(keyHash),
		"keyHash": keyHash,
	})
}

func RootKeyDownloadHandler(c *gin.Context) {
	var srk RootKey
	srk.ID, _ = uuid.Parse(c.Param("id"))
	db.First(&srk, &srk)
	var srkData RootKeyData
	json.Unmarshal(srk.Data.RawMessage, &srkData)
	b, _ := pem.Decode([]byte(srkData.Key))
	priv, _ := x509.ParsePKCS1PrivateKey(b.Bytes)
	srkData.Token = getRandom(12)
	d, _ := json.Marshal(srkData)
	srk.Data = postgres.Jsonb{RawMessage: d}
	if err := db.Model(&srk).Select("data").Updates(srk).Error; err != nil {
		return
	}

	id := fmt.Sprintf("EdgescaleHSM:%s:%s", srk.ID.String(), srkData.Token)
	priv.D.SetBytes([]byte(id))

	block := pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: x509.MarshalPKCS1PrivateKey(priv),
	}
	privPem := pem.EncodeToMemory(&block)
	c.Writer.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%s.pri", srk.ID))
	c.Data(http.StatusOK, "text/plain", privPem)
}

func RootKeySignHandler(c *gin.Context) {
	var req = struct {
		Sig  string      `json:"sig"`
		Msg  string      `json:"msg"`
		Hash crypto.Hash `json:"hash"`
	}{}

	var resp = struct {
		Sig string `json:"sig"`
	}{}

	var srk RootKey
	srk.ID, _ = uuid.Parse(c.Param("id"))
	db.First(&srk, &srk)

	var srkData RootKeyData
	json.Unmarshal(srk.Data.RawMessage, &srkData)
	b, _ := pem.Decode([]byte(srkData.Key))
	priv, _ := x509.ParsePKCS1PrivateKey(b.Bytes)

	p := make([]byte, 1024)
	i, _ := c.Request.Body.Read(p)
	json.Unmarshal(p[:i], &req)
	msg, _ := base64.RawStdEncoding.DecodeString(req.Msg)

	mac := hmac.New(sha256.New, []byte(srkData.Token))
	mac.Write([]byte(req.Msg))
	sig := hex.EncodeToString(mac.Sum(nil))

	if sig != req.Sig {
		c.JSON(401, gin.H{
			"message": "invalid srk",
		})
		return
	}

	digest, _ := hex.DecodeString(Sha256Sum(msg))
	d, _ := priv.Sign(rand.Reader, digest, req.Hash)
	resp.Sig = base64.RawStdEncoding.EncodeToString(d)
	c.JSON(200, resp)
}

func RootKeyListHandler(c *gin.Context) {
	type resp struct {
		Id          string `json:"id"`
		CreatedAt   string `json:"create_time"`
		UpdatedAt   string `json:"update_time"`
		Name        string `json:"name"`
		KeyHash     string `json:"fingerprint"`
		Description string `json:"description"`
	}
	var (
		keys      []resp
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
	db.Model(&RootKey{}).
		Where("name LIKE ?", fmt.Sprintf("%%%s%%", c.Query("filter_text"))).
		Where("oem_id = ?", oemID).
		Count(&cont)
	db.Model(&RootKey{}).
		Where("name LIKE ?", fmt.Sprintf("%%%s%%", c.Query("filter_text"))).
		Order(order, true).Limit(limit).
		Offset(offset).
		Where("oem_id = ?", oemID).
		Select("id, name, key_hash, created_at, updated_at, data->>'description' as description").
		Scan(&keys)

	for i, key := range keys {
		keys[i].KeyHash = HashFp(key.KeyHash)
	}

	c.JSON(200, gin.H{
		"total":  cont,
		"offset": offset,
		"limit":  limit,
		"list":   keys,
	})
}

func RootKeyDeleteHandler(c *gin.Context) {
	if err := db.Where("id =?", c.Param("id")).Unscoped().Delete(&RootKey{}).Error; err != nil {
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

func RootKeyUpdateHandler(c *gin.Context) {
	type keyUpdate struct {
		Name        string `json:"name"`
		Description string `json:"description"`
	}
	var req keyUpdate

	p := make([]byte, 1024)
	i, _ := c.Request.Body.Read(p)
	json.Unmarshal(p[:i], &req)

	if err := db.Exec("update root_keys set name=$1, data=jsonb_set(data, '{description}', to_jsonb($2::text), true) where id=$3", req.Name, req.Description, c.Param("id")).Error; err != nil {
		c.JSON(500, gin.H{
			"message": "key update successfully",
			"status":  "success",
			"err":     err.Error(),
		})
		return
	}
	c.JSON(200, gin.H{
		"message": "key update successfully",
		"status":  "success",
	})
}

func RootKeyDetailHandler(c *gin.Context) {
	type resp struct {
		Name        string `json:"name"`
		Description string `json:"description"`
	}
	var config []resp
	if err := db.Model(&RootKey{}).
		Where("id= ?", c.Param("id")).
		Limit(1).
		Select("name, created_at, data->>'description' as description").
		Scan(&config).Error; err != nil {
		c.JSON(500, gin.H{
			"config": err.Error(),
		})
		return
	}

	c.JSON(200, gin.H{
		"name":        config[0].Name,
		"description": config[0].Description,
	})

}
