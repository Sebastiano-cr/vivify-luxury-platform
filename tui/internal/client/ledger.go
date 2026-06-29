package client

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/Sebastiano-cr/vivify-luxury-platform/tui/internal/model"
)

type LedgerClient struct {
	BaseURL string
	http    *http.Client
}

func NewLedgerClient(baseURL string) *LedgerClient {
	return &LedgerClient{
		BaseURL: baseURL,
		http:    &http.Client{Timeout: 5 * time.Second},
	}
}

func (c *LedgerClient) GetAccounts() ([]model.Account, error) {
	resp, err := c.http.Get(c.BaseURL + "/accounts")
	if err != nil {
		return nil, fmt.Errorf("fetch accounts: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status: %s", resp.Status)
	}
	var accounts []model.Account
	if err := json.NewDecoder(resp.Body).Decode(&accounts); err != nil {
		return nil, fmt.Errorf("decode accounts: %w", err)
	}
	return accounts, nil
}

func (c *LedgerClient) GetTransactions(limit int) ([]model.Transaction, error) {
	url := fmt.Sprintf("%s/transactions?limit=%d", c.BaseURL, limit)
	resp, err := c.http.Get(url)
	if err != nil {
		return nil, fmt.Errorf("fetch transactions: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status: %s", resp.Status)
	}
	var txs []model.Transaction
	if err := json.NewDecoder(resp.Body).Decode(&txs); err != nil {
		return nil, fmt.Errorf("decode transactions: %w", err)
	}
	return txs, nil
}

func (c *LedgerClient) GetMetrics() (*model.FinanceMetrics, error) {
	resp, err := c.http.Get(c.BaseURL + "/finances/metrics")
	if err != nil {
		return nil, fmt.Errorf("fetch metrics: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status: %s", resp.Status)
	}
	var metrics model.FinanceMetrics
	if err := json.NewDecoder(resp.Body).Decode(&metrics); err != nil {
		return nil, fmt.Errorf("decode metrics: %w", err)
	}
	return &metrics, nil
}
