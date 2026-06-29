package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/lipgloss"

	"github.com/Sebastiano-cr/vivify-luxury-platform/tui/internal/style"
)

var primary = lipgloss.Color("#D4AF37")

type Provider struct {
	Name   string `json:"name"`
	Tier   string `json:"tier"`
	Status string `json:"status"`
}

type Health struct {
	Status          string     `json:"status"`
	Uptime          float64    `json:"uptime_s"`
	Providers       []Provider `json:"providers"`
	HealthyCount    int        `json:"providers_healthy"`
	TotalCount      int        `json:"providers_total"`
}

type AuditEntry struct {
	Event struct {
		Provider string  `json:"provider"`
		Score    float64 `json:"score,omitempty"`
		Model    string  `json:"model,omitempty"`
		User     string  `json:"user,omitempty"`
	} `json:"event"`
	Hash string `json:"hash"`
}

type AuditResponse struct {
	Total   int           `json:"total"`
	Entries []AuditEntry  `json:"entries"`
}

type tuiModel struct {
	ready   bool
	spinner spinner.Model
	client  *http.Client

	health      *Health
	audit       *AuditResponse
	err         error
	loading     bool
}

func initialModel() tuiModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(primary)

	return tuiModel{
		spinner: s,
		client:  &http.Client{Timeout: 5 * time.Second},
		loading: true,
	}
}

func (m tuiModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, m.fetchAll())
}

func (m tuiModel) fetchAll() tea.Cmd {
	return func() tea.Msg {
		h, err1 := func() (*Health, error) {
			resp, err := m.client.Get("http://localhost:3333/health")
			if err != nil {
				return nil, err
			}
			defer resp.Body.Close()
			var h Health
			if err := json.NewDecoder(resp.Body).Decode(&h); err != nil {
				return nil, err
			}
			return &h, nil
		}()
		if err1 != nil {
			return errMsg{err1}
		}

		a, err2 := func() (*AuditResponse, error) {
			resp, err := m.client.Get("http://localhost:3333/audit/chain?limit=10")
			if err != nil {
				return nil, err
			}
			defer resp.Body.Close()
			var a AuditResponse
			if err := json.NewDecoder(resp.Body).Decode(&a); err != nil {
				return nil, err
			}
			return &a, nil
		}()
		if err2 != nil {
			return errMsg{err2}
		}

		return dataLoadedMsg{h, a}
	}
}

type dataLoadedMsg struct {
	health *Health
	audit  *AuditResponse
}

type errMsg struct{ error }

func (m tuiModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			return m, tea.Quit
		case "r":
			m.loading = true
			return m, m.fetchAll()
		}

	case tea.WindowSizeMsg:
		m.ready = true

	case dataLoadedMsg:
		m.health = msg.health
		m.audit = msg.audit
		m.loading = false
		return m, nil

	case errMsg:
		m.err = msg
		m.loading = false
		return m, nil

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd
	}
	return m, nil
}

func (m tuiModel) View() string {
	if !m.ready {
		return "\n  Carregando LazySOC..."
	}
	if m.loading {
		return "\n  " + m.spinner.View() + " Carregando dados do SOC Gateway..."
	}
	if m.err != nil {
		return style.Card.Foreground(style.Danger).
			Render("Erro: "+m.err.Error()) + "\n\n" +
			style.Help.Render("r para tentar novamente  q para sair")
	}

	header := style.Header.Width(78).
		Render("LAZYSOC \u2014 Gateway Monitor")

	healthBox := m.renderHealth()
	auditBox := m.renderAudit()

	footer := style.Help.Width(78).Render("r refresh  q quit")

	return lipgloss.JoinVertical(lipgloss.Top, header, "", healthBox, "", auditBox, "", footer)
}

func (m tuiModel) renderHealth() string {
	h := m.health
	if h == nil {
		return style.Card.Width(78).Render("Sem dados de saúde.")
	}

	var lines []string
	uptime := time.Duration(h.Uptime) * time.Second
	uptimeStr := fmt.Sprintf("%dh%dm", int(uptime.Hours()), int(uptime.Minutes())%60)

	statusColor := style.Success
	if h.Status != "healthy" {
		statusColor = style.Danger
	}
	status := lipgloss.NewStyle().Foreground(statusColor).Render(h.Status)

	lines = append(lines, fmt.Sprintf("Status: %s  |  Uptime: %s  |  Providers: %d/%d",
		status, uptimeStr, h.HealthyCount, h.TotalCount))

	for _, p := range h.Providers {
		pColor := style.Success
		if p.Status != "up" && p.Status != "healthy" {
			pColor = style.Danger
		}
		lines = append(lines, fmt.Sprintf("  %s %-18s [%s]",
			lipgloss.NewStyle().Foreground(pColor).Render("\u25CF"),
			p.Name, p.Status))
	}

	return style.Card.Width(78).Render(
		"Sa\u00fade dos Providers\n\n" + strings.Join(lines, "\n"),
	)
}

func (m tuiModel) renderAudit() string {
	a := m.audit
	if a == nil {
		return style.Card.Width(78).Render("Sem dados de auditoria.")
	}

	lines := []string{fmt.Sprintf("\u00daltimas %d auditorias (total: %d):", len(a.Entries), a.Total)}
	for _, e := range a.Entries {
		score := e.Event.Score
		if score > 0 {
			lines = append(lines, fmt.Sprintf("  %s score=%.4f", e.Event.Provider, score))
		} else if e.Event.Model != "" {
			lines = append(lines, fmt.Sprintf("  %s model=%s user=%s", e.Event.Provider, e.Event.Model, e.Event.User))
		}
	}

	return style.Card.Width(78).Render(
		"Cadeia de Auditoria (Hashchain)\n\n" + strings.Join(lines, "\n"),
	)
}

func main() {
	if _, err := tea.NewProgram(initialModel(), tea.WithAltScreen()).Run(); err != nil {
		panic(err)
	}
}
