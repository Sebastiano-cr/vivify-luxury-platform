package main

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type tool struct {
	label string
	cmd   string
	icon  string
}

var tools = []tool{
	{"LazyLedger (finanças)", "lazyledger", "💰"},
	{"LazyVivify (joias)", "lazyvivify", "💎"},
	{"LazySOC (LLM gateway)", "lazysoc", "🧠"},
	{"LazyGit (repositórios)", "lazygit", "📦"},
	{"LazySQL (bancos)", "lazysequel", "🗄️"},
	{"LazyBackup (backups)", "lazybackup", "💾"},
	{"LazyZellij (multiplex)", "lazyzellij", "🚀"},
	{"LazyMon (monitor)", "lazymon", "📊"},
	{"---", "", ""},
	{"🔵 Deploy Blue", "deploy-vivify blue", ""},
	{"🟢 Deploy Green", "deploy-vivify green", ""},
	{"↩️ Rollback", "rollback-vivify", ""},
}

type model struct {
	cursor   int
	quitting bool
}

func (m model) Init() tea.Cmd { return nil }

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			m.quitting = true
			return m, tea.Quit
		case "up", "k":
			if m.cursor > 0 {
				m.cursor--
			}
		case "down", "j":
			if m.cursor < len(tools)-1 {
				m.cursor++
			}
		case "enter", " ":
			selected := tools[m.cursor]
			if selected.cmd == "" {
				return m, nil
			}
			cmd := exec.Command("sh", "-c", selected.cmd)
			cmd.Stdin = os.Stdin
			cmd.Stdout = os.Stdout
			cmd.Stderr = os.Stderr
			if err := cmd.Run(); err != nil {
				fmt.Printf("\nErro ao executar: %v\n", err)
				fmt.Println("Pressione Enter para voltar...")
				fmt.Scanln()
			}
			return m, nil
		}
	}
	return m, nil
}

func (m model) View() string {
	if m.quitting {
		return ""
	}

	style := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#D4AF37")).
		Padding(1, 2).
		Width(60)

	title := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#D4AF37")).
		Render("LAZYHUB \u2014 Vivify Command Center\n")

	var list strings.Builder
	for i, t := range tools {
		if t.cmd == "" {
			list.WriteString(fmt.Sprintf("  %s\n", strings.Repeat("\u2500", 50)))
			continue
		}
		cursor := " "
		if m.cursor == i {
			cursor = "\u25B8"
		}
		icon := t.icon
		list.WriteString(fmt.Sprintf("%s %s %s\n", cursor, icon, t.label))
	}

	footer := "\n" + lipgloss.NewStyle().
		Foreground(lipgloss.Color("#666")).
		Render("\u2191/\u2193 navega  |  Enter executa  |  q/ctrl+c sai")

	return style.Render(title + list.String() + footer)
}

func main() {
	if _, err := tea.NewProgram(model{}).Run(); err != nil {
		fmt.Printf("Erro: %v\n", err)
		os.Exit(1)
	}
}
