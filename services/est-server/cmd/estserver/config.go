// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"crypto"
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"gopkg.in/yaml.v2"
	"io/ioutil"
	"log"
	"time"
)

type Config struct {
	CertFile      string `yaml:"certfile"`
	KeyFile       string `yaml:"keyfile"`
	Addr          string `yaml:"addr"`
	RootCA        RootCA `yaml:"rootca"`
	BootstrapUser string `yaml:"bootstrap_user"`
	BootstrapPass string `yaml:"bootstrap_pass"`
	Expiry        time.Duration
	DefaultDays   time.Duration `yaml:"default_days"`
	TrustCAFile   string        `yaml:"trustcafile"`
	TrustRoot     x509.Certificate
	OCSPServer    []string `yaml:"ocsp_server"`
	ESAPI         string   `yaml:"es_api"`
	ESToken       string   `yaml:"es_token"`
	tlsConfig     *tls.Config
}

type RootCA struct {
	CertFile    string `yaml:"certfile"`
	KeyFile     string `yaml:"keyfile"`
	Certificate *x509.Certificate
	PrivateKey  crypto.PrivateKey
}

type StorageOptionsConf struct {
	Type     string            `json:"type"`
	Host     string            `json:"host"`
	Port     int               `json:"port"`
	Hosts    map[string]string `json:"hosts"`
	Username string            `json:"username"`
	Password string            `json:"password"`
	Database int               `json:"database"`
}

func ESTConfigLoad() *Config {
	cfg := Config{}
	yamlFile, err := ioutil.ReadFile("/etc/est/config.yaml")
	if err = yaml.Unmarshal(yamlFile, &cfg); err != nil {
		log.Fatalf("Unmarshal: %v", err)
	}
	fmt.Println(cfg)
	cfg.Expiry = cfg.DefaultDays * 24 * time.Hour
	cfg.tlsConfig = &tls.Config{}
	return &cfg
}

func (cfg *Config) ESTConfigInit() {
	root, err := tls.LoadX509KeyPair(cfg.RootCA.CertFile, cfg.RootCA.KeyFile)
	if err != nil {
		log.Fatal(err)
	}
	rootCA, err := x509.ParseCertificate(root.Certificate[0])
	if err != nil {
		log.Fatal(err)
	}
	cfg.RootCA.Certificate = rootCA
	cfg.RootCA.PrivateKey = root.PrivateKey
	fmt.Println(cfg.RootCA.Certificate.SignatureAlgorithm)
}
