package main

import (
	"fmt"
	"net/http"
)

func route(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Hello, World!")
}

func main() {
    http.HandleFunc("/", route)
    http.ListenAndServe(":10000", nil)
	fmt.Println("Server started at http://localhost:10000")
}
