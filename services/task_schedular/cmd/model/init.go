// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package model

import (
	"fmt"

	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/postgres"
)

var DB *gorm.DB

func Init(host, user, name, pwd string, port int, maxPool int, debug bool) error {
	var err error
	DB, err = gorm.Open("postgres", fmt.Sprintf("host=%s port=%d user=%s dbname=%s password=%s sslmode=disable",
		host, port, user, name, pwd))
	if err != nil {
		return err
	}
	if err := DB.DB().Ping(); err != nil {
		return err
	}

	setupDB(DB, maxPool, debug)

	return nil
}

func setupDB(db *gorm.DB, maxPool int, debug bool) {
	db.LogMode(debug)
	db.DB().SetMaxOpenConns(maxPool)
	db.DB().SetMaxIdleConns(20)
}

func Close() {
	_ = DB.Close()
}
