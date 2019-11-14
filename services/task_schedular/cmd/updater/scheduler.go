package updater

import (
	"../config"
	"../model"
	"sync"
)

func Scheduler() error {
	tasks, err := model.GetDaTasks(2000, 0)
	if err != nil {
		config.Log.Errorf("Get DaTask List, got error: %v", err)
		return err
	}
	config.Log.Infof("Scheduler started, %d need to schedule", len(tasks))

	var wg sync.WaitGroup
	for _, taskInfo := range tasks {
		wg.Add(1)
		go func() {
			defer wg.Done()
			daInstList, err := model.GetDaInstByTaskID(taskInfo.ID)
			if err != nil {
				config.Log.Errorf("GetDaInstByTaskID got error, taskID[%d], error: %v", taskInfo.ID, err)
				return
			}

			daInstStatusList := make([]int, len(daInstList))
			for _, daInstInfo := range daInstList {
				daInstStatusList = append(daInstStatusList, daInstInfo.Status)
			}

			lastStatus := taskInfo.ParseStatus(daInstStatusList)
			if taskInfo.Status != lastStatus {
				err := taskInfo.UpdateWithMap(map[string]interface{}{"status": lastStatus})
				if err != nil {
					config.Log.Errorf("Update Task, taskID[%d], error: %v", taskInfo.ID, err)
				}
			}
		}()
	}

	wg.Wait()
	return nil
}
