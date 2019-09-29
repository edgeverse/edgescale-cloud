// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

import (
	"fmt"
	"github.com/gin-gonic/gin"
	"reflect"
)

func GetEnrollEndpoints(c *gin.Context, d Device, e interface{}) {
	var trustChain = `LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSURJVENDQWdtZ0F3SUJBZ0lKQUlNT0EzQmpi
KzB2TUEwR0NTcUdTSWIzRFFFQkN3VUFNQ2N4SlRBakJnTlYKQkFNTUhFNVlVQ0JGWkdkbGMyTmhi
R1VnUTBFZ0xTQkNiMjkwYzNSeVlYQXdIaGNOTVRjeE1qRTFNVE14T0RFMwpXaGNOTWpjeE1qRXpN
VE14T0RFM1dqQW5NU1V3SXdZRFZRUUREQnhPV0ZBZ1JXUm5aWE5qWVd4bElFTkJJQzBnClFtOXZk
SE4wY21Gd01JSUJJakFOQmdrcWhraUc5dzBCQVFFRkFBT0NBUThBTUlJQkNnS0NBUUVBOGxxNldz
T1cKYk5UQm9DSERCZVIzWVRwV0xWbWZ1dk1KN1dka3RaRElNZExFeHlaTWhYd0MxSjZaL2Zmek5j
eWVtRHZnT0dESQoyenNQYmtQUmc4YjFxcXlmY1pFOE0zY3pHbEdJeUFKVC9ZTGNlQ2FBVTJwaWhB
L3Y4a2VtMmFZeStzV2ZkbVJIClU4SFV2MnNGLzFabTNlbXlpYSt1dHp5K3RIYzlkbFc5YlBJNGlu
YmN5ejVHVitIcithUjFHVjBmcWxUUVBkL3AKSitpU0sraHhMV09KL0ZmUnNaTjJTVGhLMU51RTFp
dlpkanllb1p4cHpnK2RnSXNseVkwTktuV0tIQUx5VzhQawp5YjNSakZZMDN5ck1MeEZWSjZBYzhz
SW94end1Z2k0QzVLaEJNckhhcXc1b1Q3Y0FtV3hYcmtqRVlLK3lvNTBzCjdUQ2JTcTBXdDkvZ3hR
SURBUUFCbzFBd1RqQWRCZ05WSFE0RUZnUVV6MFNIN3NyOTFYWFBiaDdyRHdwZ3Q5c0wKZnk0d0h3
WURWUjBqQkJnd0ZvQVV6MFNIN3NyOTFYWFBiaDdyRHdwZ3Q5c0xmeTR3REFZRFZSMFRCQVV3QXdF
QgovekFOQmdrcWhraUc5dzBCQVFzRkFBT0NBUUVBcXVUQXNYVXR5L3ZhTktjYnBmRTVwbHNHaVJa
RUZBVkVvVy9LCm1heVF4ZGdFZ01jN2czb1dXRTdIbTkxdkVQR2RFemFUM3BFdHpxRXVON25PSnZM
bnZUWjdZaktBeU9BYWhqMzQKNitTOFF1dzJhYkgzcWNKZ1hSMDlYM2NVMlU0aERzS3FocXJVU1RF
MEswRmFTUU9EV3dxRlNjb0p3dTl5bkhzdApET1BwbmZpbkxwUkZJcktGdFFsZk0vNUFQdnplUnVT
WDBmWWJNQVFJMEd2M0cwZ3Vya1owSzFnNzJPa1BvSkt5CjJJM3hHUEZlL2Njb0tFM0hwa01EUUN2
MWFEQ3dzZWR2Mlc2a2hUN0kyNWRsc004YVc4Zm4wWUFPZ3NCdzZLL0IKeWpNem5KRVFJV2l5dG90
b0xpYnJnNW9rZHFsQW11bkVtT2EvSkVGK0lUVWpGcG0xd2c9PQotLS0tLUVORCBDRVJUSUZJQ0FU
RS0tLS0tCi0tLS0tQkVHSU4gQ0VSVElGSUNBVEUtLS0tLQpNSUlEQ1RDQ0FmR2dBd0lCQWdJSkFM
UE1BMzBjQUZodE1BMEdDU3FHU0liM0RRRUJDd1VBTUJzeEdUQVhCZ05WCkJBTU1FRTVZVUNCRlpH
ZGxVMk5oYkdVZ1EwRXdIaGNOTVRjeE1qQTNNRGt3TmpFd1doY05NamN4TWpBMU1Ea3cKTmpFd1dq
QWJNUmt3RndZRFZRUUREQkJPV0ZBZ1JXUm5aVk5qWVd4bElFTkJNSUlCSWpBTkJna3Foa2lHOXcw
QgpBUUVGQUFPQ0FROEFNSUlCQ2dLQ0FRRUF4ZGY4MVEzVFdjUE11QVo2UnJZazh2VURjUGx5eFJ2
MzFteFFDcm9MCitCSlhzalhZZGJpZTNrUXVMZEZFbTM2Ykttd1FPQS9xb1l3SCthdm83OGFvaTZi
QWZFdHpUcE8wbzVja2lsTmsKV2FuMUMxdUlzVjBUS3k3R0hDL0JhaTRQZi9BSHpQTVQwM0lBMWd2
Vk5QWE5vWHpaNmQ4UlowOVdqRE1uUXlnNgpDN096L2dVMlhpWCtqVktXaUNQbWR6QjZTdHVkUGZX
dkVGQ0lGWkxCTWlMOHVGTWlyODk1YS96L0l2cmJ3UWZZCnl1bG4vRWs2dk1keGREU1h3SlBTZnl0
YmVYb3ZCaWNxbkNtTlF4Kzhya1hmT01tM2dHVFNNbHN4VXNFZ05ISGoKS3YyYmJhT3cyZ0JvUE5t
MTZCMVNqc0hDQ1BTZ3hCbXpOVTkvTmkrUEhacWZHUUlEQVFBQm8xQXdUakFkQmdOVgpIUTRFRmdR
VWhtcFJmRitieXJkS09lYTZZa1hjTEZManpjc3dId1lEVlIwakJCZ3dGb0FVaG1wUmZGK2J5cmRL
Ck9lYTZZa1hjTEZManpjc3dEQVlEVlIwVEJBVXdBd0VCL3pBTkJna3Foa2lHOXcwQkFRc0ZBQU9D
QVFFQUhXSW4KKzluT0xYWWVXOWxFbUhrTmtBYXRQbGlkejQvbGhhRmMyemhNMUFZcDhVWlZ4ZTJi
T09nSUFKTXJCbnBncDJORwo3d0pVQmZOMlphc0xGa3F2K3UyaUZ3ajh1bGJlMFFJZGR1RGZRQWJC
dXJ4YWtBck1lTm5RQTE1TTN3dGFVM1o5ClJYay93UVBQZDczeUFZV2JZdmNmQ0FsK2JMR0tYZFJt
NUYxVGJ2L0JycTFWYkh1Q05HRzJQT283K3JLNWk0UVkKeSs1N1FyU2VNSE5pSjFPMlpRYXJyQmw0
aWMrMkZidVlFc0MwVUpBdXBJWlBiNitYaG12TGViL1JCaFg5cHI1RQpBc3BIWEdqNldMMFZXam9r
cS9RcjBFTVA5UEtKOXlsT2ZtSVNMQzFCczRRY1lrNmw0U1lOOTJUVnlTcG1RZzdpCkVuQ2doSThH
MFh1MHM4MXlldz09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0KCg==`

	var caURI = "https://int.e-est.edgescale.org"
	var apiURI = "http://api.edgescale.org/v1"
	type deviceModel struct {
		Model   string `json:"model"`
		OwnerID string `json:"owner_id"`
	}

	var model deviceModel
	//esdb.Model(&DccaModels{}).
	esdb.Table("dcca_models").
		Select("concat(model, '.' , type, '.' , platform, '.' , vendor) as model, owner_id").
		Where("id=?", d.ModelID).
		First(&model)

	type DccaCommonService struct {
		Name string `json:"name"`
		URL  string `json:"url"`
		Port string `json:"port"`
	}
	var services []DccaCommonService
	if err := esdb.Table("dcca_common_services").
		Where("user_id= ?", model.OwnerID).
		Select("name, url, port").
		Scan(&services).Error; err != nil {
		fmt.Println(err)
	}

	for _, service := range services {
		switch service.Name {
		case "RestAPI Service":
			apiURI = service.URL
		case "Enrollment Service":
			caURI = service.URL
		}
	}

	reflect.ValueOf(e).Elem().FieldByName("CaUri").SetString(caURI)
	reflect.ValueOf(e).Elem().FieldByName("ApiUri").SetString(apiURI)
	reflect.ValueOf(e).Elem().FieldByName("TrustChain").SetString(trustChain)
	reflect.ValueOf(e).Elem().FieldByName("Model").SetString(model.Model)
}
