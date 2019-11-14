package model

import (
	"fmt"

	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/postgres"
)

var DB *gorm.DB

func Init(host, user, name, pwd string, port int, debug bool) error {
	var err error
	DB, err = gorm.Open("postgres", fmt.Sprintf("host=%s port=%d user=%s dbname=%s password=%s sslmode=disable",
		host, port, user, name, pwd))
	if err != nil {
		return err
	}
	if err := DB.DB().Ping(); err != nil {
		return err
	}

	setupDB(DB, debug)

	return nil
}

func setupDB(db *gorm.DB, debug bool) {
	db.LogMode(debug)
	db.DB().SetMaxOpenConns(2000)
	db.DB().SetMaxIdleConns(0)
}

func Close() {
	_ = DB.Close()
}
