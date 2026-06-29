package main

import (
	"fmt"
	"os/exec"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/Sebastiano-cr/vivify-luxury-platform/tui/internal/style"
)

type page int

const (
	pageMenu page = iota
	pageRunning
	pageResult
)

type model struct {
	page     page
	output   string
	err      error
	loading  bool
	cursor   int
	choices  []string
	commands []string
}

func initialModel() model {
	return model{
		page:    pageMenu,
		cursor:  0,
		choices: []string{
			"Backup agora",
			"Listar backups",
			"Abrir diretorio de backups",
		},
		commands: []string{
			"bash deploy/bin/backup.sh",
			"ls -lh /var/www/vivify/backups/db/ 2>&1 | tail -20",
			"xdg-open /var/www/vivify/backups/ 2>/dev/null || echo 'Sem ambiente grafico'",
		},
	}
}

func (m model) Init() tea.Cmd { return nil }

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch m.page {
		case pageMenu:
			switch msg.String() {
			case "ctrl+c", "q":
				return m, tea.Quit
			case "up", "k":
				if m.cursor > 0 {
					m.cursor--
				}
			case "down", "j":
				if m.cursor < len(m.choices)-1 {
					m.cursor++
				}
			case "enter":
				m.loading = true
				m.page = pageRunning
				m.err = nil
				return m, m.runCommand(m.commands[m.cursor])
			}

		case pageRunning:
			return m, nil

		case pageResult:
			switch msg.String() {
			case "q", "esc", "enter":
				m.page = pageMenu
				m.output = ""
				m.err = nil
			}
		}

	case outputMsg:
		m.loading = false
		m.output = msg.output
		m.page = pageResult
		return m, nil

	case errMsg:
		m.loading = false
		m.err = msg.err
		m.output = msg.err.Error()
		m.page = pageResult
		return m, nil
	}

	return m, nil
}

type outputMsg struct{ output string }
type errMsg struct{ err error }

func (m model) runCommand(cmdStr string) tea.Cmd {
	return func() tea.Msg {
		parts := strings.Fields(cmdStr)
		if len(parts) == 0 {
			return errMsg{fmt.Errorf("comando vazio")}
		}
		cmd := exec.Command(parts[0], parts[1:]...)
		out, err := cmd.CombinedOutput()
		if err != nil {
			return outputMsg{string(out) + "\nErro: " + err.Error()}
		}
		return outputMsg{string(out)}
	}
}

func (m model) View() string {
	switch m.page {
	case pageMenu:
		return m.viewMenu()
	case pageRunning:
		return m.viewRunning()
	case pageResult:
		return m.viewResult()
	}
	return ""
}

func (m model) viewMenu() string {
	header := style.Header.Width(60).Render("LAZYBACKUP")

	var items []string
	for i, choice := range m.choices {
		cursor := " "
		if i == m.cursor {
			cursor = lipgloss.NewStyle().Foreground(style.Primary).Render(">")
		}
		items = append(items, fmt.Sprintf("%s %s", cursor, choice))
	}

	body := style.Card.Width(60).Render(
		lipgloss.JoinVertical(lipgloss.Left, items...),
	)

	footer := style.Help.Render("\u2191/\u2193 navega  Enter executa  q sair")

	return lipgloss.JoinVertical(lipgloss.Top, header, "", body, "", footer)
}

func (m model) viewRunning() string {
	header := style.Header.Width(60).Render("LAZYBACKUP")
	body := style.Card.Width(60).Render(
		"  Executando backup...\n\n  " + lipgloss.NewStyle().Foreground(style.Secondary).Render("Aguarde..."),
	)
	return lipgloss.JoinVertical(lipgloss.Top, header, "", body)
}

func (m model) viewResult() string {
	header := style.Header.Width(60).Render("RESULTADO")

	content := m.output
	if m.err != nil {
		content = lipgloss.NewStyle().Foreground(style.Danger).Render("Erro: "+m.err.Error()) + "\n" + content
	}

	// Truncate if too long
	if len(content) > 2000 {
		content = content[:1997] + "..."
	}

	body := style.Card.Width(60).Render(content)

	footer := style.Help.Render("Enter/esc volta ao menu  q sair")

	return lipgloss.JoinVertical(lipgloss.Top, header, "", body, "", footer)
}

func main() {
	if _, err := tea.NewProgram(initialModel(), tea.WithAltScreen()).Run(); err != nil {
		panic(err)
	}
}
