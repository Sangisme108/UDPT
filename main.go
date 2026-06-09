package main

import (
	"fmt"
	"os/exec"
	"strconv"
	"strings"
)

type Agent struct {
	Name  string
	CPU   float64
	RAM   float64
	Score float64
}

func getStats(container string) (float64, float64, error) {
	cmd := exec.Command(
		"docker",
		"stats",
		container,
		"--no-stream",
		"--format",
		"{{.CPUPerc}} {{.MemPerc}}",
	)

	output, err := cmd.Output()
	if err != nil {
		return 0, 0, err
	}

	parts := strings.Fields(string(output))

	cpuStr := strings.Replace(parts[0], "%", "", -1)
	ramStr := strings.Replace(parts[1], "%", "", -1)

	cpu, _ := strconv.ParseFloat(cpuStr, 64)
	ram, _ := strconv.ParseFloat(ramStr, 64)

	return cpu, ram, nil
}

func main() {

	containers := []string{
		"dkron1",
		"dkron2",
		"dkron3",
	}

	bestScore := 999999.0
	bestAgent := ""

	fmt.Println("===== LOAD AWARE SCHEDULER =====")

	for _, c := range containers {

		cpu, ram, err := getStats(c)

		if err != nil {
			fmt.Println("Lỗi:", err)
			continue
		}

		score := cpu + ram

		fmt.Printf("%s => CPU %.2f%% | RAM %.2f%% | SCORE %.2f\n",
			c,
			cpu,
			ram,
			score)

		if score < bestScore {
			bestScore = score
			bestAgent = c
		}
	}

	fmt.Println("--------------------------------")
	fmt.Println("Node được chọn:", bestAgent)
	fmt.Println("Score:", bestScore)
}