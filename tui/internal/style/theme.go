package style

import (
	"github.com/charmbracelet/lipgloss"
)

var (
	Primary   = lipgloss.Color("#D4AF37")
	Secondary = lipgloss.Color("#666666")
	Success   = lipgloss.Color("#22c55e")
	Danger    = lipgloss.Color("#ef4444")
	Muted     = lipgloss.Color("#444444")
	BorderC   = lipgloss.Color("#333333")
	Text      = lipgloss.Color("#FFFFFF")
	Bg        = lipgloss.Color("#1A1A1A")

	Header = lipgloss.NewStyle().
		Background(Bg).
		Foreground(Primary).
		Bold(true).
		Padding(0, 2)

	Card = lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(BorderC).
		Padding(1, 2).
		Margin(0, 1)

	StatusBar = lipgloss.NewStyle().
		Background(Bg).
		Foreground(lipgloss.Color("#AAAAAA")).
		Padding(0, 2)

	Help = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#666666")).
		Padding(0, 2)
)
