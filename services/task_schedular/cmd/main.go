package main

import (
	"./config"
	"./model"
	"./updater"
	"time"

	"github.com/spf13/pflag"
)

var (
	DBHost    = pflag.StringP("db_host", "h", "127.0.0.1", "database host")
	DBPort    = pflag.IntP("db_port", "p", 5432, "database port")
	DBName    = pflag.StringP("db_name", "n", "edgescale", "database name")
	DBUser    = pflag.StringP("db_user", "u", "edgescale", "database username")
	DBPwd     = pflag.StringP("db_pwd", "w", "edgescale", "database password")
	LogLevel  = pflag.UintP("log_level", "v", 4, "debug level 0-5, 0:panic, 1:Fatal, 2:Error, 3:Warn, 4:Info 5:debug")
	CAFile    = pflag.StringP("ca_file", "a", "", "rootCA file")
	CertFile  = pflag.StringP("cert_file", "m", "", "cert file")
	KeyFile   = pflag.StringP("key_file", "k", "", "key file")
	VerifySSL = pflag.BoolP("verify_ssl", "s", false, "verify ssl")
	APPHost   = pflag.StringP("app_host", "t", "127.0.0.1", "app host")
	APPPort   = pflag.StringP("app_port", "r", "7443", "app port")
)

func main() {
	pflag.Parse()

	config.InitLog(*LogLevel)
	config.SetTlsConfig(*CAFile, *CertFile, *KeyFile, *VerifySSL)

	var debug bool
	if *LogLevel == 5 {
		debug = true
	}
	err := model.Init(*DBHost, *DBUser, *DBName, *DBPwd, *DBPort, debug)
	if err != nil {
		panic(err)
	}
	defer func() {
		_ = model.DB.Close()
	}()

	taskUpdaterTicker := time.NewTicker(time.Second * 5)
	go func() {
		for {
			select {
			case <-taskUpdaterTicker.C:
				config.Log.Infof("start update task")
				err := updater.UpdateTask(*APPHost, *APPPort)
				if err != nil {
					config.Log.Errorf("update task got error: %v", err)
				}
			}
		}
	}()

	taskSchedulerTicker := time.NewTicker(time.Second * 5)
	go func() {
		for {
			select {
			case <-taskSchedulerTicker.C:
				config.Log.Infof("start task scheduler")
				err := updater.Scheduler()
				if err != nil {
					config.Log.Errorf("task scheduler got error: %v", err)
				}
			}
		}
	}()

	select {}
}
