package config

import (
	"github.com/sirupsen/logrus"
	"task_schedular/util"
)

const (
	ResourceDeployApp      = "https://%s:%s/v1/user/%d/app"
	ResourceQueryAppStatus = "https://%s:%s/v1/user/%d/app/%s"
)

var (
	Log       *logrus.Logger
	TlsConfig util.TlsConfig
)

var (
	HEADERS = map[string]string{
		"User-Agent":   "kubectl/v1.7.0 (linux/amd64) kubernetes/d3ada01",
		"Accept":       "application/json",
		"Content-Type": "application/json",
	}
)

func InitLog(logLevel uint) {
	Log = logrus.New()
	Log.SetLevel(logrus.Level(logLevel))
	return
}

func SetTlsConfig(caFile, certFile, keyFile string, verifySSL bool) {
	TlsConfig = util.TlsConfig{
		RootCAFile: caFile,
		PemFile:    certFile,
		KeyFile:    keyFile,
		Verify:     verifySSL,
	}
}
