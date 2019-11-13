package util

import "testing"

func TestRootCARequest(t *testing.T) {
	url := "https://test.zhepoch.me:444"
	tlsConfig := TlsConfig{
		RootCAFile: "/Users/zhanghuashuai/rootca.crt",
	}

	resp, err := Get(url, map[string]string{"aa": "123"}, nil, tlsConfig)
	if err != nil {
		t.Fatal(err)
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	t.Log(resp.StatusCode)
}

func TestCertRequest(t *testing.T) {
	url := "https://test.zhepoch.me:444"
	tlsConfig := TlsConfig{
		PemFile: "/Users/zhanghuashuai/server.crt",
		KeyFile: "/Users/zhanghuashuai/server.key",
	}

	resp, err := Get(url, map[string]string{"aa": "123"}, nil, tlsConfig)
	if err != nil {
		t.Fatal(err)
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	t.Log(resp.StatusCode)
}

func TestRequest(t *testing.T) {
	url := "https://www.baidu.com"
	tlsConfig := TlsConfig{}

	resp, err := Get(url, nil, nil, tlsConfig)
	if err != nil {
		t.Fatal(err)
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	t.Log(resp.StatusCode)
}
