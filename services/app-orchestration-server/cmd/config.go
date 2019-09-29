// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"database/sql"
	"fmt"

	_ "github.com/lib/pq"
)

func ReadConfig(host string, port int, dbName, user, password string) (EdgeText, error) {
	url := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable", host, port, user, password, dbName)
	db, err := sql.Open("postgres", url)
	if err != nil {
		return EdgeText{}, err
	}
	if err := db.Ping(); err != nil {
		return EdgeText{}, err
	}
	defer db.Close()

	var edgeConfig EdgeConfig
	if err := db.QueryRow("select * from config").Scan(&edgeConfig.Text); err != nil {
		return EdgeText{}, err
	}
	return edgeConfig.Text, nil
}
