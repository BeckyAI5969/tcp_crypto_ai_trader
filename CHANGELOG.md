# Changelog

All notable changes to TCP Crypto AI Trader are documented here.

## [0.1.0] - 2026-07-12

### Added
- AI decision engine and multi-timeframe confirmation
- Risk validation and position sizing
- Dynamic leverage selection
- ATR-based stop-loss and take-profit planning
- Trade execution planning
- Paper trading execution
- Binance Futures Testnet read-only client
- Safe Testnet order validation
- Testnet account and position monitoring
- Centralized configuration with environment variables
- Structured JSON logging
- Unit and integration test framework
- GitHub Actions continuous integration

### Changed
- Main pipeline now supports execution dispatch
- Main pipeline now writes structured pipeline, trade, risk, and error logs
- Configuration defaults to PAPER mode with live trading disabled

### Security
- API keys and secrets are loaded from environment variables only
- Live trading remains disabled
- Testnet order submission requires explicit opt-in
- Sensitive fields are redacted from structured logs
