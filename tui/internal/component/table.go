package component

import (
	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/lipgloss"

	"github.com/Sebastiano-cr/vivify-luxury-platform/tui/internal/style"
)

func NewTable(columns []table.Column, rows []table.Row, height int) table.Model {
	t := table.New(
		table.WithColumns(columns),
		table.WithRows(rows),
		table.WithFocused(true),
		table.WithHeight(height),
	)

	s := table.DefaultStyles()
	s.Header = s.Header.
		BorderStyle(lipgloss.NormalBorder()).
		BorderForeground(style.BorderC).
		BorderBottom(true).
		Bold(false).
		Foreground(style.Primary)

	s.Selected = s.Selected.
		Foreground(lipgloss.Color("#FFFFFF")).
		Background(style.Primary).
		Bold(true)

	t.SetStyles(s)
	return t
}
