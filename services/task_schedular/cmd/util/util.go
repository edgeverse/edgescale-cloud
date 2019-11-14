package util

import (
	"bytes"
	"crypto/tls"
	"crypto/x509"
	"errors"
	"fmt"
	"io/ioutil"
	"net/http"
	"reflect"
	"time"
)

const (
	UnSettingTls = 1 << iota
	RootCAType   = 1 << iota
	CertType     = 1 << iota
)

func CheckLimitAndOffset(limit, offset int) (int, int) {
	if limit <= 0 {
		limit = 2000
	}
	if offset < 0 {
		offset = 0
	}
	return limit, offset
}

func ContainsInt(val int, arr []int) bool {
	for _, item := range arr {
		if reflect.DeepEqual(val, item) {
			return true
		}
	}
	return false
}

func ParseToStr(m map[string]string) string {
	values := bytes.Buffer{}
	for key, val := range m {
		values.WriteByte('&')
		values.WriteString(key)
		values.WriteByte('=')
		values.WriteString(val)
	}
	if values.Len() > 0 {
		values.Bytes()[0] = '?'
	}
	return values.String()
}

type TlsConfig struct {
	RootCAFile string
	PemFile    string
	KeyFile    string
	Verify     bool
}

func (c *TlsConfig) Type() int {
	if c.RootCAFile != "" {
		return RootCAType
	}
	if c.KeyFile != "" && c.PemFile != "" {
		return CertType
	}
	return UnSettingTls
}

func (c *TlsConfig) GenerateTlsConfig() (*tls.Config, error) {
	config := &tls.Config{}

	if !c.Verify {
		config.InsecureSkipVerify = true
	}

	switch c.Type() {
	case RootCAType:
		certPool, err := ReadRootCA(c.RootCAFile)
		if err != nil {
			return config, err
		}

		config.RootCAs = certPool
		return config, nil
	case CertType:
		cert, err := ReadCertificate(c.PemFile, c.KeyFile)
		if err != nil {
			return config, err
		}

		certPool, err := ReadRootCA(c.PemFile)
		if err != nil {
			return config, err
		}

		config.Certificates = []tls.Certificate{cert}
		config.RootCAs = certPool
		return config, nil
	}
	return config, nil
}

func ReadRootCA(caPath string) (*x509.CertPool, error) {
	certPool := x509.NewCertPool()
	caBytes, err := ioutil.ReadFile(caPath)
	if err != nil {
		return nil, err
	}
	ok := certPool.AppendCertsFromPEM(caBytes)
	if !ok {
		return nil, errors.New(fmt.Sprintf("the ca file is unable verificate"))
	}

	return certPool, nil
}

func ReadCertificate(certFile, keyFile string) (tls.Certificate, error) {
	keyBytes, err := ioutil.ReadFile(keyFile)
	if err != nil {
		return tls.Certificate{}, err
	}

	certBytes, err := ioutil.ReadFile(certFile)
	if err != nil {
		return tls.Certificate{}, err
	}

	certificate, err := tls.X509KeyPair(certBytes, keyBytes)
	return certificate, err
}

func Get(url string, param map[string]string, header map[string]string, tlsConfig TlsConfig) (*http.Response, error) {
	tc, err := tlsConfig.GenerateTlsConfig()
	if err != nil {
		return nil, err
	}

	tr := &http.Transport{
		TLSClientConfig: tc,
		IdleConnTimeout: 30 * time.Second,
	}
	client := http.Client{
		Transport: tr,
	}

	url = fmt.Sprintf("%s%s", url, ParseToStr(param))
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}

	for k, v := range header {
		req.Header.Set(k, v)
	}

	response, err := client.Do(req)
	return response, err
}
