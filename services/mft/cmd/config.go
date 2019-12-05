// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"encoding/base64"
	"gopkg.in/yaml.v2"
	"io/ioutil"
	"os"
)

type ESConf struct {
	API        string  `yaml:"api"`
	MQTT       string  `yaml:"mqtt_url"`
	ESTAPI     string  `yaml:"estapi"`
	EAPI       string  `yaml:"eapi"`
	Trustchain string  `yaml:"trustchain"`
	Mft        MftConf `yaml:"mft"`
	ESDB       ESDB    `yaml:"esdb"`
}

type ESDB struct {
	DBHost string `yaml:"dbHost"`
	DBUser string `yaml:"dbUser"`
	DBPass string `yaml:"dbPass"`
	DBName string `yaml:"dbName"`
}

type MftConf struct {
	DBHost  string `yaml:"dbHost"`
	DBUser  string `yaml:"dbUser"`
	DBPass  string `yaml:"dbPass"`
	DBName  string `yaml:"dbName"`
	ESToken string `yaml:"esToken"`
}

var esconf ESConf

func ESConfInit() {
	var (
		data    []byte
		err     error
		envConf string
		version string
	)

	if version = os.Getenv("VERSION"); version == "" {
		version = "beijing"
	}
	if envConf = os.Getenv("ES_CONF"); envConf != "" {
		data, err = base64.StdEncoding.DecodeString(envConf)
	}
	if err != nil || envConf == "" {
		if data, err = ioutil.ReadFile("/etc/edgescale/config.yaml"); err != nil {
			CloudConfig(version)
			return
		}
	}
	yaml.Unmarshal(data, &esconf)
}
