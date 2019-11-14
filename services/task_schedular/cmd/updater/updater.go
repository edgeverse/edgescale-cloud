package updater

import (
	"sync"
	"task_schedular/config"
	"task_schedular/model"
)

func UpdateTask(AppHost, AppPort string) error {
	instances, err := model.GetDaInst(2000, 0)
	if err != nil {
		config.Log.Errorf("Get DaInst, got error: %v", err)
		return err
	}
	config.Log.Infof("Start, all %d need to synchronise", len(instances))

	var wg sync.WaitGroup
	for _, instance := range instances {
		wg.Add(1)
		go func() {
			defer wg.Done()
			err := instance.UpdateStatus(AppHost, AppPort)
			if err != nil {
				config.Log.Errorf("Update status, daInstance[%d] got error: %v", instance.ID, err)
				return
			}
		}()
	}

	wg.Wait()
	return nil
}
