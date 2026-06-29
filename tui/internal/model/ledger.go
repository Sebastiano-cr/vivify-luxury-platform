package model

import "time"

type Account struct {
	ID        string  `json:"id"`
	Name      string  `json:"name"`
	Direction string  `json:"direction"`
	Balance   float64 `json:"balance"`
}

type Transaction struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Entries   []Entry   `json:"entries"`
	CreatedAt time.Time `json:"created_at"`
}

type Entry struct {
	AccountID string  `json:"account_id"`
	Direction string  `json:"direction"`
	Amount    float64 `json:"amount"`
}

type FinanceMetrics struct {
	Revenue     float64         `json:"revenue"`
	COGS        float64         `json:"cogs"`
	GrossProfit float64         `json:"gross_profit"`
	GrossMargin float64         `json:"gross_margin"`
	ByChannel   []ChannelMetric `json:"by_channel"`
	TopJewels   []JewelProfit   `json:"top_jewels"`
}

type ChannelMetric struct {
	Channel string  `json:"channel"`
	Revenue float64 `json:"revenue"`
	Profit  float64 `json:"profit"`
}

type JewelProfit struct {
	Name   string  `json:"name"`
	Profit float64 `json:"profit"`
}
