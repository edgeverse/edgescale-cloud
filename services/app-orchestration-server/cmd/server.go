// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"crypto/tls"
	"crypto/x509"
	"io/ioutil"
	"net/http"
	"time"

	"github.com/gorilla/mux"
)

// Route is the model for the router setup
type Route struct {
	Name        string
	Method      string
	Pattern     string
	HandlerFunc HandlerFunc
}

// Routes are the main setup for our Router
type Routes []Route

var kuberoutes = Routes{
	Route{"Healthcheck", "GET", "/health", HealthcheckHandler},
	Route{"ReloadCert", "POST", "/v1/reload", ReloadCertsHandler},

	Route{"queryapps", "GET", "/v1/user/{userid}/app", GetAppsHandler},
	Route{"createapp", "POST", "/v1/user/{userid}/app", CreateAppHandler},
	Route{"createapp", "GET", "/v1/user/{userid}/appsum", GetAppSumHandler},

	Route{"queryapp", "GET", "/v1/user/{userid}/app/{appname}", GetAppHandler},
	Route{"appevent", "GET", "/v1/user/{userid}/app/{appname}/event", GetAppEventLogHandler},
	Route{"applog", "GET", "/v1/user/{userid}/app/{appname}/log", GetAppLogsLogHandler},
	Route{"appreboot", "POST", "/v1/user/{userid}/app/{appname}/reboot", RestartAppHandler},
	Route{"deleteapp", "DELETE", "/v1/user/{userid}/app/{appname}", DelAppHandler},

	Route{"querynode", "GET", "/v1/nodes/{deviceid}", GetNodeHandler},
	Route{"D2CloudSync", "GET", "/v1/nodes/{deviceid}/app", D2CloudSyncHandler},

	Route{"batchcreate", "POST", "/v1/user/{userid}/task", GroupCreateAppHandler},
	Route{"gettasklist", "GET", "/v1/user/{userid}/task", GetTaskListHandler},
	Route{"gettasksum", "GET", "/v1/user/{userid}/task/{taskid}", GetTaskSumHandler},
	Route{"delgroupapp", "DELETE", "/v1/user/{userid}/task/{taskid}", GroupDeletHandler},

	Route{"flushcache", "POST", "/v1/user/{userid}/flushcache", FlushCacheHandler},
}

func StartHTTPServer(listenaddr, cafile, certfile, keyfile string) {
	//r := mux.NewRouter().StrictSlash(true)

	r := mux.NewRouter()
	for _, route := range kuberoutes {
		log.Infoln("setup http server:", route.Name, route.Pattern)
		var handler http.Handler
		handler = makeHandler(route.HandlerFunc)
		r.Methods(route.Method).
			Path(route.Pattern).
			Name(route.Name).
			Handler(handler)
	}

	pool := x509.NewCertPool()

	caCrt, err := ioutil.ReadFile(cafile)
	if err != nil {
		log.Errorln("ReadFile err:", err)
		return
	}
	pool.AppendCertsFromPEM(caCrt)

	s := &http.Server{
		Addr:         listenaddr,
		Handler:      r,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 15 * time.Second,
		TLSConfig: &tls.Config{
			ClientCAs:  pool,
			ClientAuth: tls.RequireAndVerifyClientCert,
		},
	}

	log.Fatal(s.ListenAndServeTLS(certfile, keyfile))
}
