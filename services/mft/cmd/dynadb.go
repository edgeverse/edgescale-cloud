// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"fmt"
	"os"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"
)

//https://github.com/awsdocs/aws-doc-sdk-examples/blob/master/go/example_code/dynamodb/create_item.go

type ItemInfo struct {
	EnrollStatus string `json:"enroll_status"`
	Model        string `json:"model"`
	ModelID      uint   `json:"model_id"`
}

type AuthToken struct {
	Pin string `json:"pin"`
}

type Item struct {
	DeviceID string    `json:"deviceId"`
	Fuid     string    `json:"fuid"`
	OemID    string    `json:"oem_id"`
	Info     ItemInfo  `json:"info"`
	SkPub    string    `json:"sk_pub"`
	Token    AuthToken `json:"authToken"`
	Mft      bool      `json:"mft"`
}

func DynaCreateDevice(d Device, p string, m string) {
	sess, err := session.NewSession(&aws.Config{})
	svc := dynamodb.New(sess)

	token := AuthToken{
		Pin: "secure",
	}

	info := ItemInfo{
		ModelID:      d.ModelID,
		Model:        m,
		EnrollStatus: "ACTIVE",
	}

	item := Item{
		DeviceID: d.ID.String(),
		Fuid:     d.Fuid,
		OemID:    d.OemID,
		Token:    token,
		Info:     info,
		SkPub:    p,
		Mft:      true,
	}

	av, err := dynamodbattribute.MarshalMap(item)

	if err != nil {
		fmt.Println("Got error marshalling map:")
		fmt.Println(err.Error())
		os.Exit(1)
	}

	input := &dynamodb.PutItemInput{
		Item:      av,
		TableName: aws.String("edgescale-devices-dev"),
	}

	_, err = svc.PutItem(input)

	if err != nil {
		fmt.Println("Got error calling PutItem:")
		fmt.Println(err.Error())
		os.Exit(1)
	}
}

/*
{
  "authToken": {
    "pin": "secure"
  },
  "deviceId": "f6a2db6ac2c250f29aafa1c931f8f6ea",
  "fuid": "xd",
  "info": {
    "enroll_status": "INACTIVE",
    "model": "1"
  },
  "oem_id": "1957",
  "sk_pub": "LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlHZk1BMEdDU3FHU0liM0RRRUJBUVVBQTRHTkFE\nQ0JpUUtCZ1FESDdVR09ZODRvd016RWgxaXl6VFBiYlhubgorWmJFM2lESkx6M2Jnb3gvaXNsUHRE\nSFNQRWpQVDdXYWZncGs1enk3NFB1MjhSWXJ3dmFTNmF6clBDbjhsSWhnCmk2R25IeHdmMDVuNjVm\ndjNLK3RneVcra3I4NGVHcG50K3I4clhKTXA5UXMwbm9vSThhUEJSdEVJKzMvMzVaWjMKS2ZmUFRy\neGltdXhpNWgyZ3pRSURBUUFCCi0tLS0tRU5EIFBVQkxJQyBLRVktLS0tLQ==\n"
}
*/
