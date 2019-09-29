// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"crypto"
	"crypto/ecdsa"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"math/big"
	"strings"
)

func EnrollChallengeHandler(c *gin.Context) {
	type resp struct {
		DeviceID  string `json:"device_id"`
		Challenge string `json:"challenge"`
	}

	type event struct {
		Fuid  string `json:"fuid"`
		OemID string `json:"oem_id"`
		Msg   string `json:"msg"`
		Sig   string `json:"sig"`
	}

	var (
		req       event
		dev       Device
		t         DeviceData
		challenge string
		data      DeviceData
		d         []byte
	)
	p := make([]byte, 1024)
	i, _ := c.Request.Body.Read(p)
	json.Unmarshal(p[:i], &req)

	dev.Fuid = req.Fuid
	if strings.HasPrefix(req.OemID, "x") {
		dev.OemID = req.OemID
	} else {
		dev.OemID = req.OemID[:6]
		if len(req.OemID) > 8 {
			dev.OemUID = req.OemID[8:]
		}
	}
	db.Where(&dev).First(&dev)
	if dev.Status > statusActive && dev.Status < statusCreated {
		c.JSON(401, gin.H{
			"status":  "fail",
			"message": "device inactive",
		})
		return
	}

	json.Unmarshal(dev.Data.RawMessage, &t)

	buf, err := base64.StdEncoding.DecodeString(t.Key)
	block, _ := pem.Decode(buf)
	pub, err := x509.ParsePKIXPublicKey(block.Bytes)

	if err != nil {
		fmt.Println(err.Error())
		goto respErr
	}

	switch pub := pub.(type) {
	case *rsa.PublicKey:
		h := sha256.New()
		h.Write([]byte(req.Msg))
		d := h.Sum(nil)

		sig, _ := base64.StdEncoding.DecodeString(req.Sig)
		err = rsa.VerifyPKCS1v15(pub, crypto.SHA256, d, sig)
		if err != nil {
			goto respErr
		}
	case *ecdsa.PublicKey:
		r := new(big.Int)
		r.SetString(req.Sig[64:128], 16)
		s := new(big.Int)
		s.SetString(req.Sig[128:], 16)
		mpTag, _ := hex.DecodeString(req.Sig[:64])

		msg := string(mpTag) + req.Msg
		h := sha256.New()
		h.Write([]byte(msg))
		hash := h.Sum(nil)

		ret := ecdsa.Verify(pub, hash, r, s)
		if !ret {
			goto respErr
		}
	}

	buf = make([]byte, 5)
	rand.Read(buf)
	challenge = hex.EncodeToString(buf)

	json.Unmarshal(dev.Data.RawMessage, &data)
	data.Auth.Challenge = challenge
	d, _ = json.Marshal(data)
	dev.Data.RawMessage = d
	err = db.Save(&dev).Error
	if err != nil {
		fmt.Println(err.Error())
	}
	c.JSON(200, resp{
		DeviceID:  strings.Replace(dev.ID.String(), "-", "", -1),
		Challenge: challenge,
	})
	return

respErr:
	c.JSON(401, gin.H{
		"Err": "",
	})
	return
}

func EnrollETokenHandler(c *gin.Context) {
	type event struct {
		DeviceID string `json:"device_id"`
		Sig      string `json:"sig"`
	}

	type resp struct {
		EToken     string `json:"e_token"`
		CaUri      string `json:"ca_uri"`
		ApiUri     string `json:"api_uri"`
		ChainUrl   string `json:"chain_url"`
		TrustChain string `json:"trust_chain"`
		Model      string `json:"device_model"`
	}

	var (
		req        event
		dev        Device
		t          DeviceData
		pin        = "6a934b45144e3758911efa29ed68fb2d420fa7bd568739cdcda9251fa9609b1e"
		rsp        resp
		d          []byte
		buf        []byte
		err        error
		block      *pem.Block
		pub        interface{}
		deviceName string
	)

	p := make([]byte, 1024)
	i, _ := c.Request.Body.Read(p)
	json.Unmarshal(p[:i], &req)

	dev.ID, _ = uuid.Parse(req.DeviceID)
	if err := db.Where(&dev).First(&dev).Error; err != nil {
		fmt.Println(err)
		goto respErr
	}

	json.Unmarshal(dev.Data.RawMessage, &t)

	buf, err = base64.StdEncoding.DecodeString(t.Key)
	block, _ = pem.Decode(buf)
	pub, err = x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		fmt.Println(err.Error())
		goto respErr
	}

	switch pub := pub.(type) {
	case *rsa.PublicKey:
		sig, err := base64.StdEncoding.DecodeString(req.Sig)
		h := sha256.New()
		h.Write([]byte(pin + t.Auth.Challenge))
		d := h.Sum(nil)
		err = rsa.VerifyPKCS1v15(pub, crypto.SHA256, d, sig)
		if err != nil {
			goto respErr
		}
	case *ecdsa.PublicKey:
		r := new(big.Int)
		r.SetString(req.Sig[64:128], 16)
		s := new(big.Int)
		s.SetString(req.Sig[128:], 16)
		mpTag, _ := hex.DecodeString(req.Sig[:64])

		msg := string(mpTag) + pin + t.Auth.Challenge
		h := sha256.New()
		h.Write([]byte(msg))
		hash := h.Sum(nil)

		ret := ecdsa.Verify(pub, hash, r, s)
		if !ret {
			goto respErr
		}
	}

	buf = make([]byte, 15)
	rand.Read(buf)
	rsp.EToken = hex.EncodeToString(buf)

	t.Auth.EToken = rsp.EToken
	t.Auth.IsOk = true
	d, _ = json.Marshal(t)
	dev.Data.RawMessage = d
	db.Save(&dev)
	GetEnrollEndpoints(c, dev, &rsp)
	deviceName = strings.Join([]string{strings.Replace(dev.ID.String(), "-", "", -1), rsp.Model}, ".")
	SetLifeCycle(lifeCycleAuth, deviceName)
	c.JSON(200, rsp)
	return

respErr:
	c.JSON(401, gin.H{
		"Err": "",
	})
	return
}

func EnrollAuthHandler(c *gin.Context) {
	var event = struct {
		DeviceID string `json:"device_id"`
		Token    string `json:"token"`
	}{}
	p := make([]byte, 1024)
	i, _ := c.Request.Body.Read(p)
	json.Unmarshal(p[:i], &event)

	var (
		device      Device
		err         error
		deviceData  DeviceData
		deviceModel DeviceModel
	)

	if device.ID, err = uuid.Parse(event.DeviceID); err != nil {
		goto respErr
	}
	if err = db.First(&device, &device).Error; err != nil {
		goto respErr
	}

	if err = json.Unmarshal(device.Data.RawMessage, &deviceData); err != nil {
		goto respErr
	}

	if deviceData.Auth.EToken == event.Token {
		c.JSON(200, gin.H{
			"message": "valid token",
		})
		deviceModel.ModelID = device.ModelID
		db.First(&deviceModel, &deviceModel)
		deviceName := fmt.Sprintf("%s.%s.%s.%s.%s", event.DeviceID, deviceModel.Model, deviceModel.Type, deviceModel.Platform, deviceModel.Vendor)
		SetLifeCycle(lifeCycleActive, deviceName)
		return
	}

respErr:
	c.JSON(401, gin.H{
		"message": "invalid token",
	})

}
