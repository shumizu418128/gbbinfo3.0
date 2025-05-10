package config

import (
	"log"
	"os"

	"gopkg.in/yaml.v3"
)

// 設定ファイルの構造体
type Config struct {
    AvailableYears []int `yaml:"AVAILABLE_YEARS"`
}

// 変数定義
var (
    ConfigData Config
    AvailableYears []int
    LatestYear int
)

// 設定ファイルの読み込み
func Init() {
    config, err := os.ReadFile("config.yaml")
    if err != nil {
        log.Fatalf("Failed to read config.yaml: %v", err)
    }

    err = yaml.Unmarshal(config, &ConfigData)
    if err != nil {
        log.Fatalf("Failed to parse config.yaml: %v", err)
    }

    AvailableYears = ConfigData.AvailableYears
    LatestYear = AvailableYears[0]
}
