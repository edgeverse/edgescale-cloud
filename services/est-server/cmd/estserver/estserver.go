// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

func main() {
	cfg := ESTConfigLoad()
	cfg.Serve()
}
