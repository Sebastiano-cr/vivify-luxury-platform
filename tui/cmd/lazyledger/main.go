package main

import (
	"fmt"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/lipgloss"

	"github.com/Sebastiano-cr/vivify-luxury-platform/tui/internal/client"
	"github.com/Sebastiano-cr/vivify-luxury-platform/tui/internal/component"
	"github.com/Sebastiano-cr/vivify-luxury-platform/tui/internal/model"
	"github.com/Sebastiano-cr/vivify-luxury-platform/tui/internal/style"
)

const helpText = "↑/↓ navega | Enter detalhe | r refresh | q quit | 1-4 views"

type view int

const (
	viewDashboard view = iota
	viewAccounts
	viewTransactions
	viewMetrics
)

type tuiModel struct {
	ready   bool
	current view
	spinner spinner.Model
	client  *client.LedgerClient

	accounts []model.Account
	txs      []model.Transaction
	metrics  *model.FinanceMetrics
	txTotal  float64

	table   table.Model
	err     error
	loading bool
}

func initialModel() tuiModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(style.Primary)

	return tuiModel{
		current: viewDashboard,
		spinner: s,
		client:  client.NewLedgerClient("http://localhost:3002"),
		loading: true,
		table:   table.New(),
	}
}

func (m tuiModel) Init() tea.Cmd {
	return tea.Batch(
		m.spinner.Tick,
		m.fetchAll(),
	)
}

func (m tuiModel) fetchAll() tea.Cmd {
	return func() tea.Msg {
		accounts, err := m.client.GetAccounts()
		if err != nil {
			return errMsg{err}
		}
		txs, err := m.client.GetTransactions(50)
		if err != nil {
			return errMsg{err}
		}
		metrics, err := m.client.GetMetrics()
		if err != nil {
			return errMsg{err}
		}
		return dataLoadedMsg{accounts, txs, metrics}
	}
}

type dataLoadedMsg struct {
	accounts []model.Account
	txs      []model.Transaction
	metrics  *model.FinanceMetrics
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
		case "1":
			m.current = viewDashboard
			return m, nil
		case "2":
			m.current = viewAccounts
			m.rebuildAccountTable()
			return m, nil
		case "3":
			m.current = viewTransactions
			m.rebuildTxTable()
			return m, nil
		case "4":
			m.current = viewMetrics
			return m, nil
		}

		var cmd tea.Cmd
		m.table, cmd = m.table.Update(msg)
		return m, cmd

	case tea.WindowSizeMsg:
		m.ready = true

	case dataLoadedMsg:
		m.accounts = msg.accounts
		m.txs = msg.txs
		m.metrics = msg.metrics
		m.loading = false

		m.txTotal = 0
		for _, tx := range m.txs {
			for _, e := range tx.Entries {
				m.txTotal += e.Amount
			}
		}
		m.rebuildAccountTable()
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

func (m *tuiModel) rebuildAccountTable() {
	cols := []table.Column{
		{Title: "Conta", Width: 22},
		{Title: "Tipo", Width: 10},
		{Title: "Saldo", Width: 16},
	}
	rows := make([]table.Row, 0, len(m.accounts))
	for _, a := range m.accounts {
		balance := fmt.Sprintf("R$ %.2f", a.Balance)
		dir := "Débito"
		if a.Direction == "credit" {
			dir = "Crédito"
		}
		rows = append(rows, table.Row{a.Name, dir, balance})
	}
	m.table = component.NewTable(cols, rows, 10)
}

func (m *tuiModel) rebuildTxTable() {
	cols := []table.Column{
		{Title: "ID", Width: 8},
		{Title: "Descrição", Width: 30},
		{Title: "Data", Width: 18},
		{Title: "Total (R$)", Width: 14},
	}
	rows := make([]table.Row, 0, len(m.txs))
	for _, tx := range m.txs {
		total := 0.0
		for _, e := range tx.Entries {
			total += e.Amount
		}
		tid := tx.ID
		if len(tid) > 8 {
			tid = tid[:8]
		}
		rows = append(rows, table.Row{
			tid,
			tx.Name,
			tx.CreatedAt.Format("02/01 15:04"),
			fmt.Sprintf("%.2f", total),
		})
	}
	m.table = component.NewTable(cols, rows, 15)
}

func (m tuiModel) View() string {
	if !m.ready {
		return "\n  Carregando lazyledger..."
	}
	if m.loading {
		return "\n  " + m.spinner.View() + " Carregando dados do Ledger..."
	}
	if m.err != nil {
		return style.Card.Foreground(style.Danger).
			Render("Erro: "+m.err.Error()) + "\n\n" +
			style.Help.Render("r para tentar novamente · q para sair")
	}

	header := style.Header.Width(78).
		Render("LAZYLEDGER — Controle Financeiro")

	nav := style.StatusBar.Width(78).
		Render("[1] Dashboard  [2] Contas  [3] Transações  [4] Métricas")

	var body string
	switch m.current {
	case viewDashboard:
		body = m.renderDashboard()
	case viewAccounts:
		body = style.Card.Width(78).Render(
			"Contas Contábeis\n\n" + m.table.View(),
		)
	case viewTransactions:
		body = style.Card.Width(78).Render(
			"Últimas Transações\n\n" + m.table.View(),
		)
	case viewMetrics:
		body = m.renderMetricsView()
	}

	footer := style.Help.Width(78).Render(helpText)

	return lipgloss.JoinVertical(lipgloss.Top, header, nav, "", body, "", footer)
}

func (m tuiModel) renderDashboard() string {
	if m.metrics == nil {
		return "  Nenhum dado disponível."
	}
	met := m.metrics

	card := func(label, value string) string {
		return style.Card.Width(18).Render(label + "\n" + value)
	}

	row1 := lipgloss.JoinHorizontal(lipgloss.Top,
		card("Faturamento", fmt.Sprintf("R$ %.2f", met.Revenue)),
		card("CPV", fmt.Sprintf("R$ %.2f", met.COGS)),
		card("Lucro Bruto", fmt.Sprintf("R$ %.2f", met.GrossProfit)),
		card("Margem", fmt.Sprintf("%.1f%%", met.GrossMargin)),
	)

	channels := "Canais:\n"
	if len(met.ByChannel) == 0 {
		channels += "  (nenhuma venda registrada)\n"
	}
	for _, ch := range met.ByChannel {
		channels += fmt.Sprintf("  %-14s R$ %.2f\n", ch.Channel, ch.Revenue)
	}
	channelBox := style.Card.Width(78).Render(channels)

	return lipgloss.JoinVertical(lipgloss.Top, row1, "", channelBox)
}

func (m tuiModel) renderMetricsView() string {
	if m.metrics == nil {
		return style.Card.Width(78).Render("Nenhum dado disponível.")
	}
	met := m.metrics
	s := fmt.Sprintf("Faturamento:  R$ %.2f\n", met.Revenue)
	s += fmt.Sprintf("CPV:          R$ %.2f\n", met.COGS)
	s += fmt.Sprintf("Lucro Bruto:  R$ %.2f\n", met.GrossProfit)
	s += fmt.Sprintf("Margem:       %.1f%%\n", met.GrossMargin)
	s += "\nCanais:\n"
	for _, ch := range met.ByChannel {
		s += fmt.Sprintf("  %-14s R$ %.2f\n", ch.Channel, ch.Revenue)
	}
	return style.Card.Width(78).Render(s)
}

func main() {
	if _, err := tea.NewProgram(initialModel(), tea.WithAltScreen()).Run(); err != nil {
		panic(err)
	}
}
