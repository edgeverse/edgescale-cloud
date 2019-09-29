// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"encoding/hex"
	"fmt"
	"github.com/dgrijalva/jwt-go"
	"github.com/gin-gonic/gin"
	"strconv"
	"strings"
)

type DccaUser struct {
	ID       int     `json:"id"`
	UserName string  `json:"username"`
	TypeID   int     `json:"account_type_id"`
	OemID    []uint8 `json:"oem_id"`
}

func HexToBin(x string) (b string) {
	d, _ := hex.DecodeString(x)
	for _, c := range d {
		b += fmt.Sprintf("%.8b", c)
	}
	return
}

func GetOemID(c *gin.Context) string {
	var oemid string
	if oemid = c.GetHeader("oemid"); oemid != "" {
		return oemid
	}
	var u DccaUser
	uid := GetUserID(c)
	u.ID, _ = strconv.Atoi(uid)
	esdb.First(&u, &u)
	v, err := strconv.ParseUint(string(u.OemID), 2, 64)
	if err != nil {
		return fmt.Sprintf("x%s", uid)
	}
	return fmt.Sprintf("%.8x", v)[:6]
}

func setBit(n int, pos uint) int {
	n |= (1 << pos)
	return n
}

var KEY = "x^0&*${<?@[l#~?+"

func GetUserID(c *gin.Context) string {
	if uid := c.GetHeader("uid"); uid != "" {
		return uid
	}
	gc, _ := ginLambda.GetAPIGatewayContext(c.Request)
	if uid := gc.Authorizer["principalId"]; uid != nil {

		return uid.(string)
	}
	tokenString := c.GetHeader("dcca_token")

	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		// Don't forget to validate the alg is what you expect:
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("Unexpected signing method: %v", token.Header["alg"])
		}

		// hmacSampleSecret is a []byte containing your secret, e.g. []byte("my_secret_key")
		return []byte(KEY), nil
	})
	if claims, ok := token.Claims.(jwt.MapClaims); ok && token.Valid {
		fmt.Println(claims)
		s := fmt.Sprintf("%.0f", claims["uid"].(float64))
		return s
	} else {
		fmt.Println(err)
		return ""
	}

}

func OemGetUserID(o string) string {
	if strings.HasPrefix(o, "x") {
		return o[1:]
	}
	var u DccaUser
	esdb.First(&u, "oem_id=?", HexToBin(o))
	return fmt.Sprintf("%d", u.ID)
}

type OEM struct {
	Model
	OemID   string `json:"oem_id"`
	OwnerID string `'json:"owner_id"`
}
