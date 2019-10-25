// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"crypto"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/pem"
	"fmt"
	"github.com/dgrijalva/jwt-go"
	"github.com/fullsailor/pkcs7"
	"github.com/gin-gonic/gin"
	"github.com/x-pkg/requests"
	"golang.org/x/crypto/ocsp"
	"io/ioutil"
	"log"
	"math/big"
	"net/http"
	"runtime"
	"strings"
	"time"
)

func (cfg *Config) BasicAuth(r *http.Request) bool {
	auth := strings.SplitN(r.Header.Get("Authorization"), " ", 2)
	s, _ := base64.StdEncoding.DecodeString(auth[1])
	if strings.Contains(r.Host, "b-est") {
		//Bootstrap passwd mgmt, TBD.
		return true
	}

	c := requests.New()
	c.Header.Add("dcca_token", cfg.ESToken)
	auth = strings.Split(string(s), ":")
	var body = map[string]interface{}{"device_id": auth[0], "token": auth[1]}
	c.Post(fmt.Sprintf("%s/enroll/auth", cfg.ESAPI), body)
	if c.Response.StatusCode != 200 {
		j, _ := c.Json()
		log.Println(auth, j)
		return false
	}
	return true
}

func MainHandler(c *gin.Context) {
	c.Writer.Write([]byte("------ EST Server - Copyright © 2018 ------"))
	return
}

func (cfg *Config) EnrollPkcs7(w http.ResponseWriter, r *http.Request) {
	csrBytes, err := ioutil.ReadAll(r.Body)
	csrPEM, _ := pem.Decode(csrBytes)
	if csrPEM == nil {
		log.Fatal("pemcheck", err)
	}
	csr, err := x509.ParseCertificateRequest(csrPEM.Bytes)
	if err != nil {
		log.Fatal("pemcheck", err)
	}

	csr.CheckSignature()
	if err != nil {
		log.Fatal("signature: ", err)
	}

	RootCA, _ := cfg.getRootCA("sdf")

	template := &x509.Certificate{
		Subject:               csr.Subject,
		PublicKeyAlgorithm:    csr.PublicKeyAlgorithm,
		PublicKey:             csr.PublicKey,
		SignatureAlgorithm:    RootCA.Certificate.SignatureAlgorithm,
		OCSPServer:            cfg.OCSPServer,
		CRLDistributionPoints: cfg.OCSPServer,
		BasicConstraintsValid: true,
		IsCA: false,
	}

	serialNumberLimit := new(big.Int).Lsh(big.NewInt(1), 128)
	serialNumber, err := rand.Int(rand.Reader, serialNumberLimit)
	if err != nil {
		log.Fatalf("failed to generate serial number: %s", err)
	}
	log.Println(serialNumber)

	now := time.Now()
	template.SerialNumber = serialNumber
	template.NotBefore = now.UTC()
	template.NotAfter = now.Add(cfg.Expiry).UTC()
	// TO DO: read device ID from mft db, sync serialNumber to mft db.
	// template.Subject.CommonName = ""

	cert, err := x509.CreateCertificate(rand.Reader, template, RootCA.Certificate, csr.PublicKey, RootCA.PrivateKey)
	certPkcs7, err := pkcs7.DegenerateCertificate(cert)
	w.Header().Set("Content-Type", "application/pkcs7-mime")
	w.Write(certPkcs7)

}

func (cfg *Config) getRootCA(id string) (RootCA, error) {
	var r RootCA
	cb, err := ioutil.ReadFile(cfg.RootCA.CertFile)
	if err != nil {
		log.Println(err)
	}
	kb, err := ioutil.ReadFile(cfg.RootCA.KeyFile)
	if err != nil {
		log.Println(err)
	}
	tlsCerts, err := tls.X509KeyPair(cb, kb)
	r.PrivateKey = tlsCerts.PrivateKey
	r.Certificate, err = x509.ParseCertificate(tlsCerts.Certificate[0])
	return r, err
}

func (cfg *Config) SimpleEnrollHandler(c *gin.Context) {
	log.Println("simple Enroll")
	if !cfg.BasicAuth(c.Request) {
		c.JSON(401, gin.H{
			"message": "Unauthorized",
		})
		return
	}
	cfg.EnrollPkcs7(c.Writer, c.Request)
	return
}

func (cfg *Config) SimpleReenrollHandler(c *gin.Context) {
	log.Println("simple Reenroll")

	if !cfg.BasicAuth(c.Request) {
		c.JSON(401, gin.H{
			"message": "Unauthorized",
		})
		return
	}
	if len(c.Request.TLS.PeerCertificates) == 0 {
		c.Writer.WriteHeader(http.StatusUnauthorized)
		c.Writer.Write([]byte("401 - Not authorized!"))
		return
	}
	log.Println("HTTP CERTS", c.Request.TLS.PeerCertificates[0].SerialNumber)
	cfg.EnrollPkcs7(c.Writer, c.Request)
	return
}

func (cfg *Config) JwtTokenHandler(c *gin.Context) {
	// TO DO: read secret from mft db.
	hmacSampleSecret := []byte("sadf9DFoiasdFGUYUIJOIcivmv'*(7*&^%(*SA&%%$SAHDLKJHASD&^*%ed87f6sdf*&023-04l12k3;")
	if len(c.Request.TLS.PeerCertificates) == 0 {
		c.Writer.WriteHeader(http.StatusUnauthorized)
		c.Writer.Write([]byte("401 - Not authorized!"))
		return
	}
	log.Println("Client CN:", c.Request.TLS.PeerCertificates[0].Subject.CommonName)
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"deviceID": c.Request.TLS.PeerCertificates[0].Subject.CommonName,
		"nbf":      time.Now().Unix() - 300,
		"iat":      time.Now().Unix() - 300,
		"exp":      time.Now().Unix() + 3600,
	})

	// Sign and get the complete encoded token as a string using the secret
	tokenString, _ := token.SignedString(hmacSampleSecret)
	c.Writer.Write([]byte(tokenString))
}

func (cfg *Config) OcspHandler(c *gin.Context) {
	//tlsCert, _ := tls.LoadX509KeyPair(cfg.CertFile, cfg.KeyFile)
	//x509Cert, _ := x509.ParseCertificate(tlsCert.Certificate[0])
	body, err := ioutil.ReadAll(c.Request.Body)
	or, err := ocsp.ParseRequest(body)
	RootCA, _ := cfg.getRootCA("sdfdsf")

	// TO DO: revoke certificate
	template := ocsp.Response{
		Status:       0,
		SerialNumber: or.SerialNumber,
		Certificate:  RootCA.Certificate,
		ThisUpdate:   time.Now(),
	}
	resp, _ := ocsp.CreateResponse(RootCA.Certificate, RootCA.Certificate, template, RootCA.PrivateKey.(crypto.Signer))
	log.Println("ocsp", or.SerialNumber, hex.EncodeToString(or.IssuerKeyHash), err)
	c.Writer.Write(resp)
	return
}

func (cfg *Config) Serve() {
	num := runtime.NumCPU()
	runtime.GOMAXPROCS(num)

	r := gin.Default()
	r.GET("/", MainHandler)
	r.POST("/.well-known/est/simpleenroll", cfg.SimpleEnrollHandler)
	r.POST("/.well-known/est/simplereenroll", cfg.SimpleReenrollHandler)
	r.GET("/.well-known/ocsp", cfg.OcspHandler)
	r.GET("/.well-known/jwt", cfg.JwtTokenHandler)
	http.Handle("/", r)

	caCert, err := ioutil.ReadFile(cfg.TrustCAFile)
	if err != nil {
		log.Fatal(err)
	}
	caCertPool := x509.NewCertPool()
	caCertPool.AppendCertsFromPEM(caCert)

	tlsConfig := &tls.Config{
		ClientCAs:  caCertPool,
		ClientAuth: tls.VerifyClientCertIfGiven,
		//GetConfigForClient: getConfigForClient(tls.ClientHelloInfo.SignatureSchemes),
		//Time:       func() time.Time { return time.Unix(int64(time.Now().Second()+5000), 0) },
	}
	tlsConfig.BuildNameToCertificate()

	server := &http.Server{
		Addr:      cfg.Addr,
		TLSConfig: tlsConfig,
	}

	log.Fatal(server.ListenAndServeTLS(cfg.CertFile, cfg.KeyFile))
}
