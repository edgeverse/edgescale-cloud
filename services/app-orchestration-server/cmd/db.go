// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"fmt"
	"time"

	"github.com/garyburd/redigo/redis"
	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/postgres"
)

var (
	DB        *gorm.DB
	RedisPool *redis.Pool
)

func InitDB(host, user, pass, dbname string) {
	var err error
	param := fmt.Sprintf("host=%s user=%s dbname=%s sslmode=disable password=%s", host, user, dbname, pass)
	DB, err = gorm.Open("postgres", param)
	if err != nil {
		log.Fatalln("Init Database Failed: ", err)
		panic(err)
	}

	setupDB()
}

func setupDB() {
	//DB.LogMode(true)
	DB.DB().SetMaxOpenConns(100)
	DB.DB().SetConnMaxLifetime(time.Minute * 10)
	DB.DB().SetMaxIdleConns(30)
}

func CloseDB() {
	_ = DB.Close()
}

func InitRedisDB(host, port, pass string, db int) {
	RedisPool = &redis.Pool{
		MaxIdle:     1,
		MaxActive:   500,
		IdleTimeout: 180 * time.Second,
		Dial: func() (conn redis.Conn, err error) {
			client, err := redis.Dial("tcp", fmt.Sprintf("%s:%s", host, port))
			if err != nil {
				log.Errorf("redis connect is failed: %s", err.Error())
				return nil, err
			}

			if pass != "" {
				if _, err = client.Do("AUTH", pass); err != nil {
					_ = client.Close()
					log.Errorf("redis auth is failed: %s", err.Error())
					return nil, err
				}
			}

			if _, err = client.Do("SELECT", db); err != nil {
				_ = client.Close()
				log.Errorf("redis select database is failed: %s", err.Error())
				return nil, err
			}
			return client, nil
		},
	}
}

func CloseRedisDB() {
	_ = RedisPool.Close()
}
