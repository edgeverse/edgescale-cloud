// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

// +build aws

package main

import (
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"
)

func CloudConfig(v string) {
	sess, err := session.NewSession(&aws.Config{})
	svc := dynamodb.New(sess)
	input := &dynamodb.QueryInput{
		ExpressionAttributeValues: map[string]*dynamodb.AttributeValue{
			":v1": {
				S: aws.String(v),
			},
		},
		KeyConditionExpression: aws.String("version = :v1"),
		TableName:              aws.String("edgescale_config"),
	}

	result, err := svc.Query(input)
	if err != nil {
	}
	dynamodbattribute.UnmarshalMap(result.Items[0], &esconf)
}
