// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/google/uuid"
	"sort"
	"strings"
)

type FuseConfigMap map[string]string
type FuseScrConfig struct {
	DBG_LVL              string
	DCV_0                string
	DCV_1                string
	DRV_0                string
	DRV_1                string
	FR0                  string
	FR1                  string
	ITS                  string
	K0                   string
	K1                   string
	K2                   string
	NSEC                 string
	OEM_UID_0            string
	OEM_UID_1            string
	OEM_UID_2            string
	OEM_UID_3            string
	OEM_UID_4            string
	OTPMK_0              string
	OTPMK_1              string
	OTPMK_2              string
	OTPMK_3              string
	OTPMK_4              string
	OTPMK_5              string
	OTPMK_6              string
	OTPMK_7              string
	OTPMK_FLAGS          string
	OUTPUT_FUSE_FILENAME string
	PLATFORM             string
	POVDD_GPIO           string
	WP                   string
	ZD                   string
	SRKH_0               string
	SRKH_1               string
	SRKH_2               string
	SRKH_3               string
	SRKH_4               string
	SRKH_5               string
	SRKH_6               string
	SRKH_7               string
}

func (c *FuseScrConfig) Parse(txt string) FuseConfigMap {
	var configs = make(FuseConfigMap)
	s := bufio.NewScanner(strings.NewReader(txt))
	for s.Scan() {
		if strings.HasPrefix(s.Text(), "---") {
			continue
		}
		if key, val, err := parseLine(s.Text()); err == nil {
			configs[key] = val
		}
	}
	d, _ := json.Marshal(configs)
	json.Unmarshal(d, &c)
	return configs
}

func (c *FuseScrConfig) SetOemuidUUID5(s string) string {
	uid := strings.Replace(uuid.NewSHA1(uuid.NameSpaceDNS, []byte(fmt.Sprintf("%s", s))).String(), "-", "", -1)
	c.OEM_UID_1 = uid[0:8]
	c.OEM_UID_2 = uid[8:16]
	c.OEM_UID_3 = uid[16:24]
	c.OEM_UID_4 = uid[24:32]
	return uid
}

func (c *FuseScrConfig) Marshal() ([]byte, error) {
	var m FuseConfigMap
	d, _ := json.Marshal(c)
	json.Unmarshal(d, &m)
	lines := make([]string, 0, len(m))
	for k, v := range m {
		lines = append(lines, fmt.Sprintf(`%s=%s`, k, v))
	}
	sort.Strings(lines)
	return []byte(strings.Join(lines, "\n")), nil
}

func parseLine(l string) (string, string, error) {
	var values []string
	if i := strings.Index(l, "#"); i > 0 {
		values = strings.Split(l[0:i], "=")
	} else {
		values = strings.Split(l, "=")
	}
	if len(values) == 2 {
		return values[0], values[1], nil
	}
	return "", "", errors.New("invalid config line")
}
