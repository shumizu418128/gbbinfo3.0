package main

import (
    "fmt"
    "github.com/labstack/echo/v4"
    "github.com/shumizu418128/gbbinfo3.0/internal/config"
    "github.com/shumizu418128/gbbinfo3.0/internal/handlers"
)

func main() {
    config.Init()

    e := echo.New()
    requestHandler := handlers.NewRequestHandler()
    e.GET("/", requestHandler.Handle)
    e.Start(":10000")
    fmt.Println("Server started at http://localhost:10000")
}
