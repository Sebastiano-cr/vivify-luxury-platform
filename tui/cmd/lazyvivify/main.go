package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/lipgloss"

	"github.com/Sebastiano-cr/vivify-luxury-platform/tui/internal/component"
	"github.com/Sebastiano-cr/vivify-luxury-platform/tui/internal/style"
)

// ─── Models ────────────────────────────────────────────────────────────────

type Jewel struct {
	ID        string   `json:"id"`
	Name      string   `json:"name"`
	Metal     string   `json:"metal"`
	Gemstones []string `json:"gemstones"`
	Price     float64  `json:"price"`
	Status    string   `json:"status"`
	CreatedAt string   `json:"created_at"`
}

type ProvenanceStep struct {
	StepName     string `json:"step_name"`
	Description  string `json:"description"`
	Timestamp    string `json:"timestamp"`
	DocumentHash string `json:"document_hash,omitempty"`
}

type JewelOut struct {
	ID                 string           `json:"id"`
	Name               string           `json:"name"`
	Metal              string           `json:"metal"`
	Gemstones          []string         `json:"gemstones"`
	WeightGrams        float64          `json:"weight_grams"`
	Origin             string           `json:"origin,omitempty"`
	Status             string           `json:"status"`
	Description        string           `json:"description,omitempty"`
	Price              float64          `json:"price,omitempty"`
	ImageURL           string           `json:"image_url,omitempty"`
	HashChainEntryHash string           `json:"hash_chain_entry_hash"`
	QRCodeURL          string           `json:"qr_code_url"`
	CertificateWormKey string           `json:"certificate_worm_key,omitempty"`
	CreatedAt          string           `json:"created_at"`
	UpdatedAt          string           `json:"updated_at"`
	Provenance         []ProvenanceStep `json:"provenance"`
}

type ChainEntry struct {
	EventType    string `json:"event_type"`
	JewelID      string `json:"jewel_id"`
	Timestamp    string `json:"timestamp"`
	PreviousHash string `json:"previous_hash"`
	CurrentHash  string `json:"current_hash"`
}

type ChainResponse struct {
	JewelID string       `json:"jewel_id"`
	Entries []ChainEntry `json:"entries"`
	Total   int          `json:"total"`
}

// ─── Messages ──────────────────────────────────────────────────────────────

type jewelsLoadedMsg struct{ jewels []Jewel }
type detailLoadedMsg struct{ detail *JewelOut }
type chainLoadedMsg struct{ chain *ChainResponse }
type describeDoneMsg struct{ detail *JewelOut }
type actionSuccessMsg struct{ msg string }
type actionErrorMsg struct{ err error }
type errMsg struct{ error }

// ─── View State ────────────────────────────────────────────────────────────

type viewState int

const (
	viewTable viewState = iota
	viewDetail
	viewChain
	viewConfirm
	viewDescribe
)

// ─── Model ─────────────────────────────────────────────────────────────────

type tuiModel struct {
	ready   bool
	spinner spinner.Model
	client  *http.Client
	jewels  []Jewel
	table   table.Model
	err     error
	loading bool

	state      viewState
	prevState  viewState
	detail     *JewelOut
	chain      *ChainResponse
	confirmMsg string
	confirmFn  func() tea.Cmd
	statusMsg  string
	statusOK   bool
	selectedID string
}

func initialModel() tuiModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(style.Primary)

	return tuiModel{
		spinner: s,
		client:  &http.Client{Timeout: 15 * time.Second},
		loading: true,
		table:   table.New(),
		state:   viewTable,
	}
}

func (m tuiModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, m.fetchJewels())
}

// ─── API ───────────────────────────────────────────────────────────────────

const apiBase = "http://localhost:3334/jewels"

func (m tuiModel) fetchJewels() tea.Cmd {
	return func() tea.Msg {
		resp, err := m.client.Get(apiBase + "/?limit=50")
		if err != nil {
			return errMsg{err}
		}
		defer resp.Body.Close()
		var jewels []Jewel
		if err := json.NewDecoder(resp.Body).Decode(&jewels); err != nil {
			return errMsg{err}
		}
		return jewelsLoadedMsg{jewels}
	}
}

func (m tuiModel) fetchDetail(id string) tea.Cmd {
	return func() tea.Msg {
		resp, err := m.client.Get(apiBase + "/" + id)
		if err != nil {
			return errMsg{err}
		}
		defer resp.Body.Close()
		if resp.StatusCode != 200 {
			return errMsg{fmt.Errorf("HTTP %d", resp.StatusCode)}
		}
		var d JewelOut
		if err := json.NewDecoder(resp.Body).Decode(&d); err != nil {
			return errMsg{err}
		}
		return detailLoadedMsg{&d}
	}
}

func (m tuiModel) fetchChain(id string) tea.Cmd {
	return func() tea.Msg {
		resp, err := m.client.Get(apiBase + "/" + id + "/chain")
		if err != nil {
			return errMsg{err}
		}
		defer resp.Body.Close()
		if resp.StatusCode != 200 {
			return errMsg{fmt.Errorf("HTTP %d", resp.StatusCode)}
		}
		var c ChainResponse
		if err := json.NewDecoder(resp.Body).Decode(&c); err != nil {
			return errMsg{err}
		}
		return chainLoadedMsg{&c}
	}
}

func (m tuiModel) sellJewel(id string) tea.Cmd {
	return func() tea.Msg {
		body := bytes.NewBufferString(`{"status":"vendida"}`)
		req, err := http.NewRequest("PUT", apiBase+"/"+id, body)
		if err != nil {
			return actionErrorMsg{err}
		}
		req.Header.Set("Content-Type", "application/json")
		resp, err := m.client.Do(req)
		if err != nil {
			return actionErrorMsg{err}
		}
		defer resp.Body.Close()
		if resp.StatusCode != 200 {
			return actionErrorMsg{fmt.Errorf("HTTP %d", resp.StatusCode)}
		}
		return actionSuccessMsg{"Vendida com sucesso"}
	}
}

func (m tuiModel) describeJewel(id string) tea.Cmd {
	return func() tea.Msg {
		resp, err := m.client.Post(apiBase+"/"+id+"/describe", "application/json", nil)
		if err != nil {
			return actionErrorMsg{err}
		}
		defer resp.Body.Close()
		if resp.StatusCode != 200 {
			return actionErrorMsg{fmt.Errorf("HTTP %d", resp.StatusCode)}
		}
		var d JewelOut
		if err := json.NewDecoder(resp.Body).Decode(&d); err != nil {
			return actionErrorMsg{err}
		}
		return describeDoneMsg{&d}
	}
}

// ─── Update ────────────────────────────────────────────────────────────────

func (m tuiModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		// clear feedback status on any keypress
		m.statusMsg = ""

		if m.loading && msg.String() != "ctrl+c" {
			return m, nil
		}

		switch msg.String() {
		case "ctrl+c", "q":
			return m, tea.Quit
		}

		switch m.state {
		case viewTable:
			return m.updateTableKey(msg)

		case viewDetail:
			return m.updateDetailKey(msg)

		case viewChain:
			if msg.String() == "esc" {
				m.state = m.prevState
				m.chain = nil
				return m, nil
			}
			return m, nil

		case viewConfirm:
			switch msg.String() {
			case "y":
				m.loading = true
				m.state = viewDescribe
				return m, m.confirmFn()
			case "n", "esc":
				m.state = m.prevState
				return m, nil
			}
			return m, nil

		case viewDescribe:
			return m, nil
		}

	case tea.WindowSizeMsg:
		m.ready = true

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case jewelsLoadedMsg:
		m.jewels = msg.jewels
		m.loading = false
		m.rebuildTable()
		return m, nil

	case detailLoadedMsg:
		m.detail = msg.detail
		m.loading = false
		m.state = viewDetail
		return m, nil

	case chainLoadedMsg:
		m.chain = msg.chain
		m.loading = false
		m.state = viewChain
		return m, nil

	case actionSuccessMsg:
		m.loading = false
		m.setStatus(msg.msg, true)
		m.state = viewTable
		return m, m.fetchJewels()

	case actionErrorMsg:
		m.loading = false
		m.setStatus("Erro: "+msg.err.Error(), false)
		if m.state == viewDescribe {
			m.state = viewDetail
		} else {
			m.state = m.prevState
		}
		return m, nil

	case describeDoneMsg:
		m.detail = msg.detail
		m.loading = false
		m.state = viewDetail
		m.setStatus("Descricao gerada com sucesso", true)
		return m, nil

	case errMsg:
		m.err = msg
		m.loading = false
		if m.state == viewDescribe {
			m.state = viewDetail
		}
		return m, nil
	}

	return m, nil
}

func (m *tuiModel) setStatus(msg string, ok bool) {
	m.statusMsg = msg
	m.statusOK = ok
}

func (m tuiModel) updateTableKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "r":
		m.loading = true
		return m, m.fetchJewels()

	case "enter":
		if len(m.jewels) == 0 {
			return m, nil
		}
		sel := m.table.Cursor()
		if sel >= len(m.jewels) {
			return m, nil
		}
		m.loading = true
		return m, m.fetchDetail(m.jewels[sel].ID)

	case "s":
		if len(m.jewels) == 0 {
			return m, nil
		}
		sel := m.table.Cursor()
		if sel >= len(m.jewels) {
			return m, nil
		}
		j := m.jewels[sel]
		m.selectedID = j.ID
		m.prevState = viewTable
		m.confirmMsg = fmt.Sprintf("Marcar %q como vendida?", j.Name)
		m.confirmFn = func() tea.Cmd { return m.sellJewel(j.ID) }
		m.state = viewConfirm
		return m, nil

	case "h":
		if len(m.jewels) == 0 {
			return m, nil
		}
		sel := m.table.Cursor()
		if sel >= len(m.jewels) {
			return m, nil
		}
		m.loading = true
		m.prevState = viewTable
		return m, m.fetchChain(m.jewels[sel].ID)

	case "g":
		if len(m.jewels) == 0 {
			return m, nil
		}
		sel := m.table.Cursor()
		if sel >= len(m.jewels) {
			return m, nil
		}
		j := m.jewels[sel]
		m.loading = true
		m.state = viewDescribe
		return m, m.describeJewel(j.ID)

	default:
		var cmd tea.Cmd
		m.table, cmd = m.table.Update(msg)
		return m, cmd
	}
}

func (m tuiModel) updateDetailKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.state = viewTable
		m.detail = nil
		return m, nil

	case "s":
		if m.detail == nil {
			return m, nil
		}
		m.prevState = viewDetail
		m.confirmMsg = fmt.Sprintf("Marcar %q como vendida?", m.detail.Name)
		detailID := m.detail.ID
		m.confirmFn = func() tea.Cmd { return m.sellJewel(detailID) }
		m.state = viewConfirm
		return m, nil

	case "h":
		if m.detail == nil {
			return m, nil
		}
		m.loading = true
		m.prevState = viewDetail
		return m, m.fetchChain(m.detail.ID)

	case "g":
		if m.detail == nil {
			return m, nil
		}
		m.loading = true
		m.state = viewDescribe
		return m, m.describeJewel(m.detail.ID)

	default:
		return m, nil
	}
}

// ─── View ──────────────────────────────────────────────────────────────────

func (m tuiModel) View() string {
	if !m.ready {
		return "\n  Carregando LazyVivify..."
	}

	if m.err != nil && m.state == viewTable && !m.loading {
		return style.Card.Foreground(style.Danger).
			Render("Erro: "+m.err.Error()) + "\n\n" +
			style.Help.Render("r para tentar novamente  q para sair")
	}

	var content string
	switch m.state {
	case viewTable:
		content = m.viewTable()
	case viewDetail:
		content = m.viewDetail()
	case viewChain:
		content = m.viewChain()
	case viewConfirm:
		content = m.viewConfirm()
	case viewDescribe:
		content = m.viewDescribe()
	}

	if m.statusMsg != "" {
		sc := lipgloss.NewStyle().Foreground(style.Success)
		if !m.statusOK {
			sc = lipgloss.NewStyle().Foreground(style.Danger)
		}
		bar := sc.Render("  " + m.statusMsg)
		content = lipgloss.JoinVertical(lipgloss.Top, content, "", bar)
	}

	return content
}

func (m tuiModel) viewTable() string {
	header := style.Header.Width(78).
		Render("LAZYVIVIFY \u2014 Catalogo de Joias")

	var body string
	if m.loading {
		body = style.Card.Width(78).Render(
			"\n  " + m.spinner.View() + " Carregando joias...",
		)
	} else {
		body = style.Card.Width(78).Render(
			fmt.Sprintf("Joias: %d\n\n%s", len(m.jewels), m.table.View()),
		)
	}

	footer := style.Help.Width(78).
		Render("r refresh  \u2191/\u2193 navega  Enter detalhe  s vender  h hashchain  g descrever  q quit")

	return lipgloss.JoinVertical(lipgloss.Top, header, "", body, "", footer)
}

func (m tuiModel) viewDetail() string {
	if m.detail == nil {
		return style.Help.Render("Nenhum detalhe carregado.")
	}

	d := m.detail
	gems := strings.Join(d.Gemstones, ", ")
	price := fmt.Sprintf("R$ %.2f", d.Price)
	weight := fmt.Sprintf("%.1fg", d.WeightGrams)

	lines := []string{
		style.Header.Width(78).Render("  " + d.Name),
		"",
		fmt.Sprintf("  ID:\t\t%s", shorten(d.ID, 24)),
		fmt.Sprintf("  Metal:\t%s\tPeso:\t%s", d.Metal, weight),
		fmt.Sprintf("  Pedras:\t%s", gems),
		fmt.Sprintf("  Preco:\t%s\tStatus:\t%s", price, d.Status),
	}

	if d.Origin != "" {
		lines = append(lines, fmt.Sprintf("  Origem:\t%s", d.Origin))
	}

	if d.Description != "" {
		desc := d.Description
		if len(desc) > 60 {
			desc = desc[:57] + "..."
		}
		lines = append(lines, "", "  Descricao:  "+desc)
	}

	lines = append(lines, "",
		fmt.Sprintf("  Hashchain:  %s", shorten(d.HashChainEntryHash, 16)),
		fmt.Sprintf("  QR Code:    %s", d.QRCodeURL),
	)

	if d.CertificateWormKey != "" {
		lines = append(lines,
			fmt.Sprintf("  Certificado: %s", d.CertificateWormKey),
		)
	}

	if len(d.Provenance) > 0 {
		lines = append(lines, "", "  ─── Proveniencia ───")
		for _, p := range d.Provenance {
			t := p.Timestamp
			if len(t) > 16 {
				t = t[:16]
			}
			h := ""
			if p.DocumentHash != "" {
				h = " [" + shorten(p.DocumentHash, 8) + "]"
			}
			lines = append(lines,
				fmt.Sprintf("  %s\t%s%s", t, p.StepName, h),
			)
		}
	} else {
		lines = append(lines, "", "  (sem proveniencia registrada)")
	}

	body := style.Card.Width(78).Render(
		lipgloss.JoinVertical(lipgloss.Left, lines...),
	)

	footer := style.Help.Width(78).
		Render("s vender  h hashchain  g descrever  esc voltar  q quit")

	return lipgloss.JoinVertical(lipgloss.Top, body, "", footer)
}

func (m tuiModel) viewChain() string {
	if m.chain == nil {
		return style.Help.Render("Nenhuma hashchain carregada.")
	}

	header := style.Header.Width(78).
		Render("  HASHCHAIN")

	var entries []string
	if len(m.chain.Entries) == 0 {
		entries = []string{"  (nenhuma entrada na hashchain)"}
	} else {
		for i, e := range m.chain.Entries {
			t := e.Timestamp
			if len(t) > 16 {
				t = t[:16]
			}
			entries = append(entries,
				fmt.Sprintf("  %d. %s", i+1, e.EventType),
				fmt.Sprintf("     %s", t),
				fmt.Sprintf("     hash: %s", shorten(e.CurrentHash, 16)),
				"",
			)
		}
		// remove trailing blank
		entries = entries[:len(entries)-1]
	}

	summary := fmt.Sprintf("  Total: %d entradas", m.chain.Total)
	entries = append([]string{summary, ""}, entries...)

	body := style.Card.Width(78).Render(
		lipgloss.JoinVertical(lipgloss.Left, entries...),
	)

	footer := style.Help.Width(78).
		Render("esc voltar  q quit")

	return lipgloss.JoinVertical(lipgloss.Top, header, "", body, "", footer)
}

func (m tuiModel) viewConfirm() string {
	box := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(style.Danger).
		Padding(1, 3).
		Width(50).
		Align(lipgloss.Center).
		Render(
			lipgloss.JoinVertical(lipgloss.Center,
				lipgloss.NewStyle().Foreground(style.Danger).Render("Confirmar"),
				"",
				m.confirmMsg,
				"",
				lipgloss.NewStyle().Foreground(style.Secondary).Render("y sim   n nao"),
			),
		)

	return "\n\n\n" + lipgloss.PlaceHorizontal(78, lipgloss.Center, box)
}

func (m tuiModel) viewDescribe() string {
	body := style.Card.Width(78).Render(
		"\n  " + m.spinner.View() + " Gerando descricao com IA...\n\n" +
			style.Help.Render("Aguarde, isso pode levar alguns segundos."),
	)

	return lipgloss.JoinVertical(lipgloss.Top, body, "")
}

// ─── Helpers ───────────────────────────────────────────────────────────────

func shorten(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}

func (m *tuiModel) rebuildTable() {
	cols := []table.Column{
		{Title: "Nome", Width: 22},
		{Title: "Metal", Width: 12},
		{Title: "Pedras", Width: 14},
		{Title: "Preco", Width: 12},
		{Title: "Status", Width: 14},
	}
	rows := make([]table.Row, 0, len(m.jewels))
	for _, j := range m.jewels {
		price := fmt.Sprintf("R$ %.0f", j.Price)
		gems := strings.Join(j.Gemstones, ", ")
		rows = append(rows, table.Row{j.Name, j.Metal, gems, price, j.Status})
	}
	m.table = component.NewTable(cols, rows, 18)
}

// ─── Main ──────────────────────────────────────────────────────────────────

func main() {
	if _, err := tea.NewProgram(initialModel(), tea.WithAltScreen()).Run(); err != nil {
		panic(err)
	}
}
