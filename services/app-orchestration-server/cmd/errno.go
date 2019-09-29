// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

type Errno struct {
	Message string
}

func (err *Errno) Error() string {
	return err.Message
}

var (
	AppExist    = &Errno{Message: "app exist"}
	AppNotExist = &Errno{Message: "app not exist"}
	ErrDatabase = &Errno{Message: "Database error."}
	ErrRedis    = &Errno{Message: "Redis error."}
)
