package model

import (
	"../config"
	"../util"
	"database/sql/driver"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"reflect"
	"time"

	"github.com/google/uuid"
	"github.com/jinzhu/gorm/dialects/postgres"
)

const (
	DaTaskStatusReady = iota
	DaTaskStatusPending
	DaTaskStatusCreating
	DaTaskStatusStarting
	DaTaskStatusFailed
	DaTaskStatusRunning
	DaTaskStatusDeleting
	DaTaskStatusDeleted
	DaTaskStatusTimeout
	DaTaskStatusError
	DaTaskStatusK8sNoResponse
	DaTaskStatusStartFail
	DaTaskStatusInputError
	DaTaskStatusAppNotFound

	DaTaskStatusUnknown = -1
)

var (
	DaTaskScheduled = []int{DaTaskStatusReady, DaTaskStatusPending, DaTaskStatusCreating,
		DaTaskStatusStarting, DaTaskStatusRunning, DaTaskStatusDeleting}
	DaTaskCanEnd = []int{DaTaskStatusDeleted, DaTaskStatusTimeout, DaTaskStatusError,
		DaTaskStatusK8sNoResponse, DaTaskStatusInputError, DaTaskStatusAppNotFound}
	//DaTaskFail = []int{DaTaskStatusFailed, DaTaskStatusTimeout, DaTaskStatusError,
	//	DaTaskStatusK8sNoResponse, DaTaskStatusInputError, DaTaskStatusAppNotFound}
)

type DaStatusPayloadItemMetadata struct {
	CreationTimestamp string `json:"creationTimestamp"`
	Name              string `json:"name"`
	NodeName          string `json:"nodename"`
}

type DaStatusPayloadItemStatus struct {
	Phase     string `json:"phase"`
	Message   string `json:"message"`
	Reason    string `json:"reason"`
	StartTime string `json:"startTime"`
	HostIP    string `json:"hostIP"`
}

type DaStatusPayloadItem struct {
	Status   DaStatusPayloadItemStatus   `json:"status"`
	Metadata DaStatusPayloadItemMetadata `json:"metadata"`
}

type DaStatusPayload struct {
	Code       int                   `json:"code"`
	Items      []DaStatusPayloadItem `json:"items"`
	ApiVersion string                `json:"apiVersion"`
	Limit      int                   `json:"limit"`
	Offset     int                   `json:"offset"`
	Total      int                   `json:"total"`
	Status     string                `json:"status"`
}

func (p DaStatusPayload) Value() (driver.Value, error) {
	b, err := json.Marshal(p)
	if err != nil {
		return nil, err
	}
	return b, nil
}

func (p *DaStatusPayload) Scan(value interface{}) error {
	if data, ok := value.([]byte); ok {
		return json.Unmarshal(data, p)
	}
	return errors.New(fmt.Sprint("Failed to unmarshal DaStatusPayload value:", value))
}

// es_task_da_inst
type EsTaskDaInst struct {
	ID            uuid.UUID       `gorm:"type:uuid;primary_key;unique;default:uuid_generate_v1mc();"`
	TaskID        int             `gorm:"not null"`
	DeviceID      int             `gorm:"not null"`
	SoftappID     int             `gorm:"not null"`
	Status        int             `gorm:"default:0"`
	StatusPayload DaStatusPayload `gorm:"not null"`
	CreatedAt     *time.Time      `gorm:"not null;default:timezone('utc'::text, now())"`
	UpdatedAt     *time.Time      `gorm:"not null;default:timezone('utc'::text, now())"`
	Payload       postgres.Jsonb  `gorm:"not null"`
}

func (EsTaskDaInst) TableName() string {
	return "es_task_da_inst"
}

func (e *EsTaskDaInst) UpdateWithMap(m map[string]interface{}) error {
	if _, ok := m["id"]; !ok {
		m["id"] = e.ID
	}
	return DB.Model(e).Update(m).Error
}

func (e *EsTaskDaInst) GetStatusPayloadName() (string, bool) {
	items := e.StatusPayload.Items
	if len(items) == 0 {
		return "", false
	}

	return items[0].Metadata.Name, true
}

func (e *EsTaskDaInst) GetStatusPayloadPhase() (string, bool) {
	items := e.StatusPayload.Items
	if len(items) == 0 {
		return "", false
	}

	return items[0].Status.Phase, true
}

func (*EsTaskDaInst) StatusFilter(status string) int {
	switch status {
	case "Pending":
		return DaTaskStatusPending
	case "Creating":
		return DaTaskStatusCreating
	case "Starting":
		return DaTaskStatusStarting
	case "Failed":
		return DaTaskStatusFailed
	case "Running":
		return DaTaskStatusRunning
	case "Deleting":
		return DaTaskStatusDeleting
	case "Deleted":
		return DaTaskStatusDeleted
	}
	return DaTaskStatusUnknown
}

func (e *EsTaskDaInst) UpdateStatus(host, port string) error {
	if reflect.DeepEqual(e.StatusPayload, DaStatusPayload{}) {
		e.Status = DaTaskStatusK8sNoResponse
		goto UpdateStatus
	}

	if e.StatusPayload.Status == "fail" {
		e.Status = DaTaskStatusError
		goto UpdateStatus
	}

	if e.StatusPayload.Code == 0 {
		name, ok := e.GetStatusPayloadName()
		if !ok {
			e.Status = DaTaskStatusStartFail
			goto UpdateStatus
		}

		task, err := GetTaskByID(e.TaskID)
		if err != nil {
			return err
		}

		queryUrl := fmt.Sprintf(config.ResourceQueryAppStatus, host, port, task.OwnerID, name)
		resp, err := util.Get(queryUrl, nil, config.HEADERS, config.TlsConfig)
		if err != nil {
			return err
		}
		defer func() {
			_ = resp.Body.Close()
		}()

		body, err := ioutil.ReadAll(resp.Body)
		if err != nil {
			return err
		}

		var newStatusPayload DaStatusPayload
		if err := json.Unmarshal(body, &newStatusPayload); err != nil {
			return err
		}

		if newStatusPayload.Code == 404 {
			e.Status = DaTaskStatusDeleted

			if phase, ok := e.GetStatusPayloadPhase(); ok && phase != "Deleted" {
				e.StatusPayload.Items[0].Status.Phase = "Deleted"
			}
			goto UpdateStatusAndPayload
		}

		e.StatusPayload = newStatusPayload
		phase, _ := e.GetStatusPayloadPhase()
		latestStatus := e.StatusFilter(phase)

		if e.Status != latestStatus {
			config.Log.Infof("DaInst %v, Task %d changing status from %s to %s.",
				e.ID, e.TaskID, e.Status, latestStatus)
			e.Status = latestStatus
		}
		goto UpdateStatusAndPayload
	}

	if util.ContainsInt(e.StatusPayload.Code, []int{400, 401}) {
		if e.Status != DaTaskStatusInputError {
			config.Log.Infof("DaInst %v, Task %d changing status from %d to %d.",
				e.ID, e.TaskID, e.Status, DaTaskStatusInputError)
			e.Status = DaTaskStatusInputError
		}
		goto UpdateStatus
	}

	if e.StatusPayload.Code == 404 {
		if e.Status != DaTaskStatusDeleted {
			config.Log.Infof("DaInst %v, Task %d changing status from %d to %d.",
				e.ID, e.TaskID, e.Status, DaTaskStatusDeleted)
			e.Status = DaTaskStatusDeleted
		}
		goto UpdateStatus
	}
	goto UpdateStatus

UpdateStatus:
	config.Log.Debugf("update task: %v", map[string]interface{}{"status": e.Status})
	return e.UpdateWithMap(map[string]interface{}{"status": e.Status})
UpdateStatusAndPayload:
	config.Log.Debugf("update task: %v", map[string]interface{}{"status": e.Status, "status_payload": e.StatusPayload})
	return e.UpdateWithMap(map[string]interface{}{"status": e.Status, "status_payload": e.StatusPayload})
}

func GetDaInst(limit, offset int) (di []EsTaskDaInst, err error) {
	limit, offset = util.CheckLimitAndOffset(limit, offset)

	err = DB.Where("status NOT IN (?)", DaTaskCanEnd).Limit(limit).Offset(offset).
		Order("created_at desc").Find(&di).Error
	return
}

func GetDaInstByTaskID(taskID int) (di []EsTaskDaInst, err error) {
	err = DB.Where("task_id = ?", taskID).Order("created_at desc").Find(&di).Error
	return
}
