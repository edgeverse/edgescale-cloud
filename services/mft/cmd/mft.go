// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/hmac"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/tls"
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
	"github.com/x-pkg/requests"
	"gopkg.in/yaml.v2"
	"io/ioutil"
	"math/big"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"text/template"
	"time"
)

const (
	letters    = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
	lettersLen = 36
)

type Model struct {
	ID        uuid.UUID  `gorm:"type:uuid;primary_key;default:uuid_generate_v4()" json:"id"`
	CreatedAt time.Time  `json:"created_at"`
	UpdatedAt time.Time  `json:"updated_at"`
	DeletedAt *time.Time `json:"deleted_at"`
}

type ESConfig struct {
	API string    `yaml:"api" json:"keyID,omitempty"`
	MFT MFTConfig `yaml:"mft" json:"mft"`
}

type MFTConfig struct {
	KeyID      string        `yaml:"keyID,omitempty" json:"keyID,omitempty"`
	Platform   string        `yaml:"platform,omitempty" json:"platform,omitempty"`
	OemID      string        `yaml:"oemID,omitempty" json:"oemID,omitempty"`
	Key        string        `yaml:"key" json:"key"`
	FuseConfig FuseScrConfig `yaml:"fuseConfig,omitempty" json:"fuseConfig,omitempty"`
	OemUID     []string      `yaml:"oem_uid" json:"oemUID,omitempty"`
}

type MFTData struct {
	Key   string   `json:"key"`
	SKPUB string   `json:"sk_pub"`
	Tags  []string `json:"tags"`
}

type Projects struct {
	Model
	Name          string         `gorm:"type:varchar(100);unique_index:idx_name_oemid;not null" json:"name"`
	Number        uint           `json:"number"`
	CustomerID    *uuid.UUID     `gorm:"type:uuid" json:"customer_id"`
	DeviceModelID uint           `gorm:"column:model_id" json:"model_id"`
	OemID         string         `gorm:"type:varchar(64);unique_index:idx_name_oemid;not null" json:"oemID"`
	FuseConfigID  *uuid.UUID     `gorm:"type:uuid" json:"fuse_config_id"`
	IsFuse        bool           `gorm:"type:bool" json:"is_fuse"`
	Data          postgres.Jsonb `json:"data"`
}

type Customer struct {
	Model
	Name  string         `gorm:"type:varchar(100)" json:"name"`
	OemID string         `gorm:"type:varchar(64)" json:"oem_id"`
	Data  postgres.Jsonb `json:"data"`
}

type Device struct {
	Model
	Name      string         `gorm:"type:varchar(100)" json:"name"`
	Fuid      string         `gorm:"type:varchar(32)" json:"fuid"`
	OemID     string         `gorm:"type:varchar(64)" json:"oem_id"`
	SkHash    string         `gorm:"type:varchar(64)" json:"sk_hash"`
	MpTag     string         `gorm:"type:varchar(64)" json:"mp_tag"`
	ModelID   uint           `json:"model_id"`
	OemUID    string         `gorm:"type:varchar(64)" json:"oem_uid"`
	Status    uint           `json:"status"`
	ProjectID *uuid.UUID     `json:"project_id"`
	Data      postgres.Jsonb `json:"data"`
}

type DeviceData struct {
	Key     string     `json:"key"`
	KeyType int        `json:"key_type"`
	Auth    EnrollAuth `json:"auth"`
}

type EnrollAuth struct {
	Challenge string `json:"challenge"`
	EToken    string `json:"e_token"`
	IsOk      bool   `json:"is_ok"`
}

type DeviceModel struct {
	Model
	DeviceModel string         `gorm:"type:varchar(30)" json:"model"`
	Type        string         `gorm:"type:varchar(30)" json:"type"`
	Vendor      string         `gorm:"type:varchar(30)" json:"vendor"`
	Platform    string         `gorm:"type:varchar(30)" json:"platform"`
	ModelID     uint           `gorm:"unique;not null" json:"model_id"`
	Data        postgres.Jsonb `json:"data"`
}

type Resp struct {
	Status string
	Error  string
}

func MftCreateHandler(c *gin.Context) {
	type ProjectCreate struct {
		Name         string     `json:"name"`
		Number       uint       `json:"number"`
		Model        string     `json:"model"`
		ModelID      uint       `json:"model_id"`
		Customer     string     `json:"customer,omitempty"`
		CustomerID   string     `json:"customer_id,omitempty"`
		Tags         []string   `json:"tags"`
		FuseConfigID *uuid.UUID `json:"fuse_config_id"`
		IsFuse       bool       `json:"is_fuse"`
	}

	var req ProjectCreate

	p := make([]byte, 1024)
	i, _ := c.Request.Body.Read(p)
	json.Unmarshal(p[:i], &req)

	model := strings.Split(req.Model, "-")
	if req.Number < 1 {
		c.JSON(http.StatusOK, gin.H{
			"message": "Invalid Number",
			"status":  "failed",
		})
	}

	if len(model) != 4 {
		c.JSON(http.StatusOK, gin.H{
			"message": "Invalid device model",
			"status":  "failed",
		})
	}

	var newProject = Projects{
		Name:          req.Name,
		Number:        req.Number,
		DeviceModelID: req.ModelID,
		FuseConfigID:  req.FuseConfigID,
		IsFuse:        req.IsFuse,
		OemID:         GetOemID(c),
	}
	var data MFTData
	data.Tags = req.Tags
	d, _ := json.Marshal(data)
	newProject.Data = postgres.Jsonb{RawMessage: d}
	if customer_id, err := uuid.Parse(req.CustomerID); err == nil {
		newProject.CustomerID = &customer_id
		if err := db.Create(&Customer{
			Name:  req.Customer,
			Model: Model{ID: customer_id},
			OemID: GetOemID(c),
		}).Error; err != nil {
			fmt.Println(err)
		}
	}

	if err := db.Create(&newProject).Error; err != nil {
		errs := err.(*pq.Error)
		c.JSON(http.StatusOK, gin.H{
			"message": "duplicate key value: name",
			"status":  "failed",
			"code":    errs.Code,
			"err":     err.Error(),
		})
		return
	}

	if err := db.Create(&DeviceModel{
		DeviceModel: model[0],
		Type:        model[1],
		Vendor:      model[2],
		Platform:    model[3],
		ModelID:     req.ModelID,
	}).Error; err != nil {
		fmt.Println(err)
	}

	c.JSON(200, gin.H{
		"message": "create config file successfully",
		"status":  "success",
	})
}

func MftDeleteHandler(c *gin.Context) {
	//db.Where("id =?", c.Param("id")).Delete(&Projects{})
	db.Where("id =?", c.Param("id")).Unscoped().Delete(&Projects{})
	c.JSON(200, gin.H{
		"message": "delete config file successfully",
		"status":  "success",
	})
}
func MftListHandler(c *gin.Context) {
	type Resp struct {
		ID         string `json:"id"`
		Name       string `json:"name"`
		Number     string `json:"number"`
		CreatedAt  string `json:"create_time"`
		Model      string `json:"model"`
		Customer   string `json:"customer"`
		FuseConfig string `json:"fuse_config"`
	}

	var (
		projects  []Resp
		cont      uint64
		limit     = "10"
		offset    = "0"
		order     = "created_at DESC"
		orderType = "DESC"
	)
	oem_id := GetOemID(c)
	db.Table("projects").
		Where("name LIKE ?", fmt.Sprintf("%%%s%%", c.Query("filter_text"))).
		Where("oem_id = ?", oem_id).
		Count(&cont)

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
		case "created":
			order = "created_at" + " " + orderType
		default:
			order = "created_at" + " " + orderType
		}
	}

	if dbc := db.Table("projects").
		Where("projects.name LIKE ?", fmt.Sprintf("%%%s%%", c.Query("filter_text"))).
		Order(order, true).Limit(limit).
		Offset(offset).
		Select("projects.id, projects.name, customers.name as customer, projects.number, projects.created_at, concat(device_models.device_model, '-' ,device_models.type, '-' ,device_models.vendor, '-' ,device_models.platform) as model, fuse_configs.name as fuse_config").
		Where("projects.oem_id = ?", oem_id).
		Joins("left join device_models on device_models.model_id = projects.model_id").
		Joins("left join customers on customers.id = projects.customer_id").
		Joins("left join fuse_configs on fuse_configs.id = projects.fuse_config_id").
		Scan(&projects); dbc.Error != nil {
		c.JSON(500, gin.H{
			"message": "failed to query projects",
			"error":   dbc.Error,
		})
		return
	}

	c.JSON(200, gin.H{
		"total":  cont,
		"offset": offset,
		"limit":  limit,
		"list":   projects,
	})
}

func MftStatisticsHandler(c *gin.Context) {
	var (
		count uint
		pid   string
	)
	pid = c.Param("id")
	type resp struct {
		ID        string         `json:"id"`
		Name      string         `json:"name"`
		Customer  string         `json:"customer"`
		Number    uint           `json:"number"`
		CreatedAt time.Time      `json:"created_at"`
		Data      postgres.Jsonb `json:"data"`
	}
	var r resp
	db.Model(&Device{}).Where("project_id = ?", pid).Count(&count)
	db.Model(&Projects{}).
		Where("projects.id = ?", pid).
		Select("projects.id, projects.name, projects.number, projects.created_at, projects.data, customers.name as customer").
		Joins("left join customers on customers.id = projects.customer_id").Scan(&r)
	c.JSON(200, gin.H{
		"ID":             r.ID,
		"name":           r.Name,
		"customer":       r.Customer,
		"number":         r.Number,
		"online_number":  count,
		"offline_number": count - count,
		"active_number":  count,
		"create_time":    r.CreatedAt,
	})
}

func MftListDevicesHandler(c *gin.Context) {
	type model struct {
		Model    string `json:"model"`
		Type     string `json:"type"`
		Vendor   string `json:"vendor"`
		Platform string `json:"platform"`
	}
	type device struct {
		Id        string    `json:"name"`
		CreatedAt time.Time `json:"created_at"`
		UpdatedAt time.Time `json:"updated_at"`
		Mode      model     `gorm:"embedded" json:"mode"`
		Status    string    `json:"status"`
	}
	var (
		dev       []device
		count     uint = 0
		limit          = "10"
		offset         = "0"
		order          = "created_at DESC"
		orderType      = "DESC"
	)
	pid, _ := uuid.Parse(c.Param("id"))
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
	db.Model(&Device{}).Where("project_id = ?", pid).Count(&count)
	p := Projects{Model: Model{ID: pid}}
	db.Model(&Projects{}).Scan(&p)
	if err := db.Model(&Device{}).
		Where("project_id = ?", pid).
		Order(order, true).Limit(limit).
		Offset(offset).
		Select("devices.id as id, devices.created_at, devices.updated_at, device_models.device_model as model, device_models.type as type, device_models.vendor as vendor, device_models.platform as platform").
		Joins("left join device_models on devices.model_id = device_models.model_id").
		Scan(&dev).Error; err != nil {
	}
	c.JSON(200, gin.H{
		"total":   count,
		"model":   p.DeviceModelID,
		"results": dev,
	})
}

func MftCreateDevicePrepHandler(c *gin.Context) {
	var device Device
	sn := strings.Split(c.Query("fuid"), ":")
	device.Fuid = sn[0]
	if len(sn) > 1 {
		device.OemID = sn[1][:6]
		device.OemUID = sn[1][8:]
	} else {
		oemid := GetOemID(c)
		device.OemID = oemid
	}
	if err := db.Where(&device).First(&device).Error; err == nil {
		if id := device.ID.String(); id != "" {
			c.Writer.Write([]byte("\"" + strings.Replace(device.ID.String(), "-", "", -1) + "\""))
			return
		}
	}
	if len(sn) > 1 {
		c.JSON(404, gin.H{
			"status":  "fail",
			"message": "oem device not upload",
		})
		return
	}
	deviceID := uuid.NewSHA1(uuid.NameSpaceDNS, []byte(fmt.Sprintf("%s%s%s", device.OemID, device.OemUID, device.Fuid)))
	device.Model.ID = deviceID
	device.Status = statusNew
	db.Save(&device)
	c.Writer.Write([]byte("\"" + strings.Replace(deviceID.String(), "-", "", -1) + "\""))
}

func MftCreateDeviceKeyHandler(c *gin.Context) {
	var device Device
	deviceName := strings.Split(c.Query("device_name"), ".")
	oemid := GetOemID(c)
	device.ID, _ = uuid.Parse(deviceName[0])
	if strings.HasPrefix(oemid, "x") {
		device.OemID = oemid
	}
	if err := db.Where(&device).First(&device).Error; err != nil {
		c.JSON(201, gin.H{
			"error": err.Error(),
		})
		return
	}

	var model DccaModels
	if len(deviceName) > 4 {
		model.Model = deviceName[1]
		model.Type = deviceName[2]
		model.Platform = deviceName[3]
		model.Vendor = deviceName[4]
		if err := esdb.First(&model, &model).Error; err != nil {
			fmt.Println(err.Error())
		}
		device.ModelID = model.ID
	}

	priv, _ := rsa.GenerateKey(rand.Reader, 1024)
	priv.Public()
	block := pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: x509.MarshalPKCS1PrivateKey(priv),
	}
	privPem := pem.EncodeToMemory(&block)

	derPkix, err := x509.MarshalPKIXPublicKey(&priv.PublicKey)
	if err != nil {
		return
	}
	block = pem.Block{
		Type:  "PUBLIC KEY",
		Bytes: derPkix,
	}
	pubPem := pem.EncodeToMemory(&block)

	var sc = struct {
		DeviceKey string
		DeviceID  string
	}{
		DeviceKey: string(privPem),
		DeviceID:  fmt.Sprintf("%s:%s", device.Fuid, oemid),
	}
	var data DeviceData
	json.Unmarshal(device.Data.RawMessage, &data)
	data.Key = base64.StdEncoding.EncodeToString(pubPem)
	d, _ := json.Marshal(data)
	device.Data = postgres.Jsonb{RawMessage: d}
	device.Status = statusCreated
	db.Save(&device)
	t := template.New("test template")
	if data.KeyType == deviceKeySW {
		t, _ = t.Parse(bootstrapEnrollTpl)
	} else {
		t, _ = t.Parse(bootstrapEnrollSecureTpl)
	}

	t.Execute(c.Writer, sc)
}

func MftCreateDeviceHandler(c *gin.Context) {
	type deviceCreate struct {
		Sig     string `json:"sig"`
		FUID    string `json:"fuid"`
		OemID   string `json:"oem_id"`
		KeyID   string `json:"key_id"`
		KeyHash string `json:"sk_hash"`
		SkPub   string `json:"sk_pub"`
	}

	var req deviceCreate
	p := make([]byte, 1024)
	i, _ := c.Request.Body.Read(p)
	json.Unmarshal(p[:i], &req)
	var token MFTData

	var dev Device

	dev.Fuid = req.FUID
	dev.OemID = req.OemID
	dev.SkHash = req.KeyHash

	var s Projects
	db.Where("id =?", req.KeyID).First(&s)
	json.Unmarshal(s.Data.RawMessage, &token)

	mac := hmac.New(sha256.New, []byte(token.Key))
	mac.Write([]byte(req.FUID))
	sig := hex.EncodeToString(mac.Sum(nil))

	if sig == req.Sig {
		var count uint
		db.Model(&Device{}).Where("project_id = ?", req.KeyID).Count(&count)
		id, _ := uuid.Parse(req.KeyID)
		p := Projects{Model: Model{ID: id}}
		db.Where(&p).First(&p)
		if count >= p.Number {
			c.JSON(200, gin.H{
				"status":  "failed",
				"message": "Device quota limit has been reached",
			})
			return
		}

		var data DeviceData
		dev.ProjectID = &id
		dev.ModelID = s.DeviceModelID
		dev.Model.ID = uuid.NewSHA1(uuid.NameSpaceDNS, []byte(fmt.Sprintf("%s%s", req.FUID, req.OemID)))

		db.Where(&dev).First(&dev)
		json.Unmarshal(dev.Data.RawMessage, &data)
		data.Key = req.SkPub
		d, _ := json.Marshal(data)
		dev.Data = postgres.Jsonb{RawMessage: d}

		model := DeviceModel{ModelID: dev.ModelID}
		db.Where(&model).First(&model)
		dev_model := fmt.Sprintf("%s.%s.%s.%s", model.DeviceModel, model.Type, model.Platform, model.Vendor)
		dev_name := fmt.Sprintf("%s.%s", strings.Replace(dev.Model.ID.String(), "-", "", -1), dev_model)
		rb := map[string]interface{}{"names": []string{dev_name}, "user_id": OemGetUserID(p.OemID), "model_id": dev.ModelID, "customer_id": p.CustomerID}
		fmt.Printf("%v", rb)
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
			return
		}
		var deviceData DeviceData
		deviceData.Key = base64.StdEncoding.EncodeToString([]byte(req.SkPub))
		rawData, _ := json.Marshal(deviceData)
		dev.Data = postgres.Jsonb{RawMessage: rawData}

		db.Save(&dev)
		//DynaCreateDevice(dev, req.SkPub, dev_model)
		c.JSON(200, gin.H{
			"status":  "success",
			"message": result["message"],
		})
		return
	}

	c.JSON(401, gin.H{
		"status":  "failed",
		"message": "Invalid MFT token",
	})
}

func MftConfigDownloadHandler(c *gin.Context) {
	var (
		f        FuseConfig
		data     MFTData
		cc       ESConfig
		fusedata FuseConfigData
		fuse     FuseScrConfig
	)
	var p = struct {
		Projects
		Platform string `json:"platform"`
	}{}
	cc.MFT.Key = getRandom(32)
	cc.API = esconf.API
	cc.MFT.KeyID = c.Param("id")
	cc.MFT.OemID = GetOemID(c)
	p.Model.ID, _ = uuid.Parse(c.Param("id"))
	if err := db.Table("projects").
		Where("projects.id = ?", p.ID).
		Select("projects.id, projects.is_fuse, projects.data, projects.number, projects.fuse_config_id, device_models.platform").
		Joins("left join device_models on device_models.model_id = projects.model_id").
		First(&p).Error; err != nil {
		fmt.Println(err.Error())
	}

	if p.IsFuse {
		f.Model.ID = *p.FuseConfigID
		db.Where(&f).First(&f)
		json.Unmarshal(f.Data.RawMessage, &fusedata)
		fuse.Parse(fusedata.Config)
		pid := p.ID.String()
		if err := os.RemoveAll(fmt.Sprintf("/dev/shm/%s", pid)); err != nil {
			fmt.Println(err)
		}
		if err := os.Mkdir(fmt.Sprintf("/dev/shm/%s", pid), 0700); err != nil {
			fmt.Println(err)
		}
		if strings.HasPrefix(cc.MFT.OemID, "x") {
			c.JSON(403, gin.H{
				"status":  "fail",
				"message": "fuse service only supported for OEM",
			})
			return
		}
		//24 bits oemID, 8 bits reserved.
		fuse.OEM_UID_0 = cc.MFT.OemID + "00"
		for id := p.Number; id < p.Number*2; id++ {
			oemuid := fuse.SetOemuidUUID5(fmt.Sprintf("%s-%d", pid, id))
			cc.MFT.OemUID = append(cc.MFT.OemUID, oemuid)
			fuse.OUTPUT_FUSE_FILENAME = fmt.Sprintf("/dev/shm/%s/fc_%s.bin", pid, oemuid)
			f, _ := fuse.Marshal()
			if err := ioutil.WriteFile(fmt.Sprintf("/dev/shm/%s/fc_%s.ini", pid, oemuid), f, 0644); err != nil {
				fmt.Println(err)
			}
			cmd := fmt.Sprintf("./gen_fusescr /dev/shm/%s/fc_%s.ini", pid, oemuid)
			out, err := exec.Command("bash", "-c", cmd).Output()
			if err != nil {
				fmt.Println(err, string(out))
			}
			cmd = fmt.Sprintf("./fiptool create --fuse-prov /dev/shm/%s/fc_%s.bin /dev/shm/%s/fc_%s.fip", pid, oemuid, pid, oemuid)
			out, err = exec.Command("bash", "-c", cmd).Output()
			if err != nil {
				fmt.Println(err, string(out))
			}
		}
		cc.MFT.FuseConfig = fuse
		projectConfig, _ := yaml.Marshal(cc)
		if err := ioutil.WriteFile(fmt.Sprintf("/dev/shm/%s/fuse_config.yaml", pid), projectConfig, 0644); err != nil {
			fmt.Println(err)
		}
		cmd := fmt.Sprintf("rm /dev/shm/%s/*.bin && cd /dev/shm && tar czf /dev/shm/fuse-%s.tgz %s", pid, pid, pid)
		out, err := exec.Command("bash", "-c", cmd).Output()
		if err != nil {
			fmt.Println(err, string(out))
			c.JSON(200, gin.H{
				"status":  "failed",
				"message": err.Error(),
			})
			cmd = fmt.Sprintf("rm -r /dev/shm/%s && rm /dev/shm/fuse-%s.tgz %s", pid, pid, pid)
			exec.Command("bash", "-c", cmd).Output()
			return
		}
		c.FileAttachment(fmt.Sprintf("/dev/shm/fuse-%s.tgz", pid), fmt.Sprintf("fuse-%s.tgz", pid))
		cmd = fmt.Sprintf("rm -r /dev/shm/%s && rm /dev/shm/fuse-%s.tgz %s", pid, pid, pid)
		exec.Command("bash", "-c", cmd).Run()
		return
	}
	json.Unmarshal(p.Data.RawMessage, &data)
	data.Key = cc.MFT.Key
	d, _ := json.Marshal(data)
	p.Data = postgres.Jsonb{RawMessage: d}

	err := db.Model(&p.Projects).Select("data").Updates(p.Projects).Error
	if err != nil {
		c.JSON(200, gin.H{
			"status":  "failed",
			"message": err.Error(),
		})
		return
	}

	b, _ := yaml.Marshal(cc)
	c.Writer.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%s.yml", p.ID))
	c.Data(http.StatusOK, "text/plain", b)
}

func MftUpdateHandler(c *gin.Context) {
	var (
		p    Projects
		data MFTData
		err  error
		pid  string
	)
	var req = struct {
		SKX string `json:"sk_pub_x"`
		SKY string `json:"sk_pub_y"`
	}{}

	pid = c.Param("id")
	p.ID, err = uuid.Parse(pid)
	p.OemID = GetOemID(c)

	err = db.Model(&Projects{}).
		First(&p, &p).Error
	if err != nil {
		c.JSON(200, gin.H{
			"status":  "fail",
			"message": "no such project",
		})
	}

	b := make([]byte, 1024)
	i, _ := c.Request.Body.Read(b)
	json.Unmarshal(b[:i], &req)

	json.Unmarshal(p.Data.RawMessage, &data)

	x := new(big.Int)
	y := new(big.Int)
	x.SetString(req.SKX, 16)
	y.SetString(req.SKY, 16)
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
	data.SKPUB = base64.StdEncoding.EncodeToString(pemEncodedPub)
	d, _ := json.Marshal(data)
	p.Data = postgres.Jsonb{RawMessage: d}
	db.Save(&p)
	c.JSON(200, gin.H{
		"status": "success",
	})

}

func getRandom(n int) string {
	charsLength := big.NewInt(int64(lettersLen))
	b := make([]byte, n)
	for i := range b {
		r, _ := rand.Int(rand.Reader, charsLength)
		b[i] = letters[r.Int64()]

	}
	return string(b)
}
