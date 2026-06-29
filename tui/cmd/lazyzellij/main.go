package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
)

func main() {
	layout := os.Getenv("ZELLIJ_LAYOUT")
	if layout == "" {
		// Find layout relative to the binary
		exe, _ := os.Executable()
		base := filepath.Dir(exe)
	candidates := []string{
		filepath.Join(base, "../deploy/zellij/vivify.kdl"),
		filepath.Join(base, "../../deploy/zellij/vivify.kdl"),
		"./deploy/zellij/vivify.kdl",
		"/etc/vivify/deploy/zellij/vivify.kdl",
	}
		for _, c := range candidates {
			if _, err := os.Stat(c); err == nil {
				layout = c
				break
			}
		}
	}
	if layout == "" {
		fmt.Fprintln(os.Stderr, "Erro: layout vivify.kdl nao encontrado. Defina ZELLIJ_LAYOUT")
		os.Exit(1)
	}

	zellij, err := exec.LookPath("zellij")
	if err != nil {
		fmt.Fprintln(os.Stderr, "Erro: zellij nao instalado. Instale com: cargo install zellij")
		os.Exit(1)
	}

	cmd := exec.Command(zellij, "--layout", layout)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		if runtime.GOOS != "windows" {
			if exit, ok := err.(*exec.ExitError); ok {
				os.Exit(exit.ExitCode())
			}
		}
		fmt.Fprintln(os.Stderr, "Erro ao executar zellij:", err)
		os.Exit(1)
	}
}
