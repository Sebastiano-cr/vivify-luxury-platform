package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/lipgloss"

	"github.com/Sebastiano-cr/vivify-luxury-platform/tui/internal/style"
)

type ServiceStatus struct {
	Status string `json:"status"`
	Code   int    `json:"code"`
	Label  string `json:"label"`
	Error  string `json:"error,omitempty"`
}

type HealthSummary struct {
	Timestamp string                    `json:"timestamp"`
	Overall   string                    `json:"overall"`
	Services  map[string]ServiceStatus `json:"services"`
	Up        int                       `json:"up"`
	Total     int                       `json:"total"`
}

type model struct {
	ready     bool
	spinner   spinner.Model
	client    *http.Client
	summary   *HealthSummary
	err       error
	loading   bool
	lastFetch time.Time
}

func initialModel() model {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(style.Primary)
	return model{
		spinner: s,
		client:  &http.Client{Timeout: 8 * time.Second},
		loading: true,
	}
}

func (m model) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, m.fetchHealth())
}

func (m model) fetchHealth() tea.Cmd {
	return func() tea.Msg {
		resp, err := m.client.Get("http://127.0.0.1:3334/monitoring/health")
		if err != nil {
			return errMsg{err}
		}
		defer resp.Body.Close()
		var s HealthSummary
		if err := json.NewDecoder(resp.Body).Decode(&s); err != nil {
			return errMsg{err}
		}
		return healthLoadedMsg{&s}
	}
}

type healthLoadedMsg struct{ summary *HealthSummary }
type errMsg struct{ error }

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			return m, tea.Quit
		case "r":
			m.loading = true
			return m, m.fetchHealth()
		}

	case tea.WindowSizeMsg:
		m.ready = true

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case healthLoadedMsg:
		m.summary = msg.summary
		m.loading = false
		m.lastFetch = time.Now()
		m.err = nil
		return m, nil

	case errMsg:
		m.err = msg
		m.loading = false
		return m, nil
	}

	return m, nil
}

func (m model) View() string {
	if !m.ready {
		return "\n  Carregando lazymon..."
	}
	if m.loading {
		return "\n  " + m.spinner.View() + " Verificando servicos..."
	}
	if m.err != nil {
		return style.Card.Foreground(style.Danger).
			Render("Erro: "+m.err.Error()) + "\n\n" +
			style.Help.Render("r tentar novamente  q sair")
	}
	if m.summary == nil {
		return style.Help.Render("Nenhum dado.")
	}

	header := style.Header.Width(60).
		Render("LAZYMON \u2014 Monitor")

	upColor := style.Success
	if m.summary.Overall != "ok" {
		upColor = style.Danger
	}
	statusLine := fmt.Sprintf("Status: %s    Servicos: %d/%d",
		m.summary.Overall, m.summary.Up, m.summary.Total)
	statusStyle := lipgloss.NewStyle().Foreground(upColor)

	var lines []string
	lines = append(lines, "", fmt.Sprintf("  %s", statusStyle.Render(statusLine)))

	svcOrder := []string{"vivify", "ledger", "soc", "ollama", "odysseus"}
	for _, key := range svcOrder {
		svc, ok := m.summary.Services[key]
		if !ok {
			continue
		}
		icon := "\u2714"
		labelColor := style.Success
		switch svc.Status {
		case "up":
			icon = "\u2714"
			labelColor = style.Success
		case "down", "error":
			icon = "\u2718"
			labelColor = style.Danger
		case "timeout":
			icon = "\u23F3"
			labelColor = style.Secondary
		default:
			icon = "?"
			labelColor = style.Secondary
		}
		extra := ""
		if svc.Error != "" {
			extra = " (" + svc.Error + ")"
		}
		colored := lipgloss.NewStyle().Foreground(labelColor)
		lines = append(lines, fmt.Sprintf("  %s %s%s",
			colored.Render(icon),
			colored.Render(fmt.Sprintf("%-14s %s", svc.Label, svc.Status)),
			extra,
		))
	}

	lines = append(lines, "",
		fmt.Sprintf("  Ultima verificacao: %s", m.lastFetch.Format("15:04:05")),
	)

	body := style.Card.Width(60).Render(
		lipgloss.JoinVertical(lipgloss.Left, lines...),
	)

	footer := style.Help.Width(60).Render("r refresh  q quit")

	return lipgloss.JoinVertical(lipgloss.Top, header, "", body, "", footer)
}

func main() {
	if _, err := tea.NewProgram(initialModel(), tea.WithAltScreen()).Run(); err != nil {
		panic(err)
	}
}
