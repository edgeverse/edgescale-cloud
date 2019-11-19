// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package model

import (
	"../util"
	"database/sql"
	"time"

	"github.com/jinzhu/gorm/dialects/postgres"
)

const (
	TaskStatusReady = iota
	TaskStatusScheduled
	TaskStatusCanceled
	TaskStatusFail
	TaskStatusStarted
	TaskStatusComplete
	TaskStatusStartFail

	TaskTypeApp = 0
)

var (
	TaskStatusHealthy = []int{TaskStatusReady, TaskStatusScheduled, TaskStatusStarted}
	TaskStatusNames   = map[int]string{
		TaskStatusReady:     "Created",
		TaskStatusScheduled: "Scheduled",
		TaskStatusCanceled:  "Canceled",
		TaskStatusFail:      "Fail",
		TaskStatusStarted:   "Started",
		TaskStatusComplete:  "Complete",
		TaskStatusStartFail: "StartFail",
	}
)

// es_tasks
type EsTask struct {
	ID            int            `gorm:"primary_key;unique;default:nextval('es_tasks_id_seq'::regclass)"`
	Type          int            `gorm:"not null;default:0"`
	Status        int            `gorm:"not null;default:0"`
	Payloads      postgres.Jsonb `gorm:"not null"`
	CreatedAt     *time.Time     `gorm:"not null;default:timezone('utc'::text, now())"`
	OwnerID       int            `gorm:"not null"`
	LogicalDelete sql.NullBool   `gorm:"default:false"`
	StartedAt     *time.Time     `gorm:"not null;default:timezone('utc'::text, now())"`
	EndedAt       *time.Time     `gorm:"not null;default:timezone('utc'::text, now())"`
}

func (EsTask) TableName() string {
	return "es_tasks"
}

func (e *EsTask) Update() error {
	return DB.Save(e).Error
}

func (e *EsTask) UpdateWithMap(em map[string]interface{}) error {
	if _, ok := em["id"]; !ok {
		em["id"] = e.ID
	}
	return DB.Model(e).Update(em).Error
}

func (*EsTask) ParseStatus(statuses []int) int {
	for _, status := range statuses {
		if util.ContainsInt(status, DaTaskScheduled) {
			return TaskStatusScheduled
		}
	}
	return TaskStatusComplete
}

func GetDaTasks(limit, offset int) (es []EsTask, err error) {
	limit, offset = util.CheckLimitAndOffset(limit, offset)

	err = DB.Where("type = ? AND status in (?) AND logical_delete = ?",
		TaskTypeApp,
		TaskStatusHealthy,
		false).Limit(limit).Offset(offset).
		Order("created_at desc").Find(&es).Error
	return
}

func GetTaskByID(id int) (es EsTask, err error) {
	err = DB.Where("id = ?", id).First(&es).Error
	return es, err
}
