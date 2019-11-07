// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"bufio"
	"bytes"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/tls"
	"crypto/x509"
	"encoding/base64"
	"encoding/csv"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/jinzhu/gorm/dialects/postgres"
	"github.com/lib/pq"
	"github.com/x-pkg/requests"
	"io"
	"math/big"
	"strings"
)

var (
	deviceKeySW   = 0
	deviceKeyCAAM = 1
	deviceKeySE   = 2
)

//DeviceGetEndpoints TBD
func DeviceGetEndpoints(c *gin.Context) {
	type endpoint struct {
		Name        string
		URL         string
		Port        string
		AccessToken string
		O           string `json:"owner_id"`
	}
	var resp []endpoint
	dn := strings.SplitN(c.Param("id"), ".", 4)
	esdb.Table("dcca_models").Where("model = ?, type = ?, platform = ?, vendor = ?", dn[1], dn[2], dn[3], dn[4]).
		Select("owner_id").
		Scan(&resp)
	fmt.Println(resp)
}

func DeviceBatchCreateHandle(c *gin.Context) {
	var req = struct {
		Data  string `json:"data"`
		KeyID string `json:"key_id"`
		Key   string `json:"key"`
	}{}

	p := make([]byte, 1024*1024*10)
	i, _ := c.Request.Body.Read(p)
	json.Unmarshal(p[:i], &req)

	in, _ := base64.StdEncoding.DecodeString(req.Data)
	x := bytes.NewReader(in)
	r := csv.NewReader(bufio.NewReader(x))
	var (
		strX    string
		strY    string
		fuid    string
		oemID   string
		keyhash string
		skPub   string
		skb     string
		mpTag   string
	)
	tx := db.Begin()
	if req.KeyID != "" {
		var (
			p        Projects
			dev      Device
			devData  DeviceData
			mftData  MFTData
			devNames []string
		)
		db.Model(&Projects{}).
			First(&p, &p)
		json.Unmarshal(p.Data.RawMessage, &mftData)
		if mftData.SKPUB == "" {
			c.JSON(200, gin.H{
				"status":  "fail",
				"message": "secure public key not upload",
			})
			return
		}
		model := DeviceModel{ModelID: p.DeviceModelID}
		db.Where(&model).First(&model)
		for {
			record, err := r.Read()
			if err == io.EOF {
				break
			}
			if record[0] == "FUID" {
				continue
			}
			fuid = strings.Replace(record[0], "_", "", -1)
			oemID = strings.Replace(record[1], "_", "", -1)
			mpTag = strings.Replace(record[5], "_", "", -1)
			p.ID, err = uuid.Parse(req.KeyID)
			if err != nil {
				c.JSON(200, gin.H{
					"status":  "fail",
					"message": "secure public key not upload",
				})
				return
			}
			dev.ProjectID = &p.ID
			dev.MpTag = mpTag
			dev.ModelID = p.DeviceModelID

			dev.ID = uuid.NewSHA1(uuid.NameSpaceDNS, []byte(fuid+oemID+keyhash))
			dev.Fuid = fuid
			dev.OemID = oemID[:6]
			dev.OemUID = oemID[8:]
			devData.Key = mftData.SKPUB
			devData.KeyType = deviceKeyCAAM
			d, _ := json.Marshal(devData)
			dev.Data = postgres.Jsonb{RawMessage: d}

			devModel := fmt.Sprintf("%s.%s.%s.%s", model.DeviceModel, model.Type, model.Platform, model.Vendor)
			devName := fmt.Sprintf("%s.%s", strings.Replace(dev.ID.String(), "-", "", -1), devModel)

			if err := tx.Save(&dev).Error; err != nil {
				c.JSON(200, gin.H{
					"status":  "fail",
					"message": fmt.Sprintf("create device %s failed", dev.OemUID),
					"code":    err.(*pq.Error).Code,
				})
				tx.Rollback()
				return
			}
			dev.OemID = oemID
			//DynaCreateDevice(dev, mftData.SKPUB, devModel)
			devNames = append(devNames, devName)

		}
		rb := map[string]interface{}{"names": devNames, "user_id": GetUserID(c), "model_id": dev.ModelID, "customer_id": p.CustomerID}
		r := requests.New()
		r.TLSConfig = &tls.Config{
			InsecureSkipVerify: true,
		}
		r.Header.Add("dcca_token", esconf.Mft.ESToken)
		r.Post(fmt.Sprintf("%s/devices/register", esconf.API), rb)
		result, _ := r.Json()
		if result["status"] != "success" {
			c.JSON(200, gin.H{
				"status":  "failed",
				"message": result["message"],
			})
			tx.Rollback()
			return
		}
		tx.Commit()
	} else {
		for {
			record, err := r.Read()
			if err == io.EOF {
				break
			}
			if record[0] == "FUID" {
				continue
			}
			if err != nil {
				fmt.Println(err)
			}
			x := new(big.Int)
			y := new(big.Int)
			strX = strings.TrimSpace(record[2])
			strY = strings.TrimSpace(record[3])
			fuid = strings.TrimSpace(record[0])
			oemID = strings.TrimSpace(record[1])

			if skb != strX+strY {
				x.SetString(strX, 16)
				y.SetString(strY, 16)
				pub := &ecdsa.PublicKey{
					Curve: elliptic.P256(),
					X:     x,
					Y:     y,
				}
				x509EncodedPub, _ := x509.MarshalPKIXPublicKey(pub)
				pemEncodedPub := pem.EncodeToMemory(&pem.Block{
					Type:  "PUBLIC KEY",
					Bytes: x509EncodedPub,
				})
				skPub = base64.StdEncoding.EncodeToString(pemEncodedPub)
				keyhash = Sha1Sum([]byte(strX + strY))
			}

			var dev Device
			var devData DeviceData

			dev.ID = uuid.NewSHA1(uuid.NameSpaceDNS, []byte(fuid+oemID+keyhash))
			dev.Fuid = fuid
			dev.OemID = oemID[:7]
			dev.OemUID = oemID[8:]
			devData.Key = skPub
			devData.KeyType = deviceKeyCAAM
			d, _ := json.Marshal(devData)
			dev.Data = postgres.Jsonb{RawMessage: d}
			err = tx.Save(&dev).Error
			if err != nil {
				c.JSON(200, gin.H{
					"status":  "fail",
					"message": fmt.Sprintf("create device %s failed", dev.OemUID),
					"code":    err.(*pq.Error).Code,
				})
				tx.Rollback()
				return
			}

			dev.OemID = oemID
			//DynaCreateDevice(dev, skPub, "")
			skb = strX + strY

		}
		tx.Commit()
	}
	c.JSON(200, gin.H{
		"status": "success",
	})
}

func DeviceBatchDeleteHandler(c *gin.Context) {
	var req = struct {
		deviceID []string `json:"devices"`
	}{}

	d := make([]byte, 1024*1024*10)
	i, _ := c.Request.Body.Read(d)
	json.Unmarshal(d[:i], &req)

	tx := db.Begin()
	for id := range req.deviceID {
		err := tx.Where("id =? and oem_id=?", id, GetOemID(c)).Unscoped().Delete(&Device{}).Error
		if err != nil {
			tx.Rollback()
			c.JSON(200, gin.H{
				"message": "delete devices failed",
				"status":  "fail",
			})
			return
		}
	}
	tx.Commit()
	c.JSON(200, gin.H{
		"message": "delete devices successfully",
		"status":  "success",
	})
}
