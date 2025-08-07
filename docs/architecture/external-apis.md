# External APIs

## OANDA API

- **Purpose:** Real-time forex market data and historical price feeds for major currency pairs (EUR/USD, GBP/USD, USD/JPY)
- **Documentation:** https://developer.oanda.com/rest-live-v20/introduction/
- **Base URL(s):** 
  - Live: `https://api-fxtrade.oanda.com`
  - Demo: `https://api-fxpractice.oanda.com`
- **Authentication:** Bearer token authentication with API key
- **Rate Limits:** 120 requests/minute for REST, unlimited WebSocket connections

**Key Endpoints Used:**
- `GET /v3/instruments/{instrument}/candles` - Historical OHLCV data
- `GET /v3/pricing/stream` - Real-time price streaming
- `GET /v3/accounts/{accountID}/pricing` - Current market prices
- `GET /v3/instruments` - Available trading instruments

**Integration Notes:** Primary data source for forex analysis. WebSocket connection required for sub-second price updates. Handle reconnection logic for stream interruptions.

## Polygon.io API

- **Purpose:** Real-time and historical market data for major indices (US30, NAS100, SPX500) and supplementary forex data
- **Documentation:** https://polygon.io/docs/
- **Base URL(s):** `https://api.polygon.io`
- **Authentication:** API key via query parameter or header
- **Rate Limits:** 5 calls/minute (basic), 1000 calls/minute (professional)

**Key Endpoints Used:**
- `GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}` - Historical aggregates
- `WebSocket wss://socket.polygon.io/` - Real-time market data
- `GET /v3/reference/tickers` - Available symbols and metadata
- `GET /v2/last/trade/{ticker}` - Latest trade information

**Integration Notes:** Backup data source and primary for indices. WebSocket requires subscription management. Implement fallback to OANDA for forex if Polygon fails.

## TradeLocker API

- **Purpose:** Direct trade execution on prop firm accounts, real-time position management, multi-account support
- **Documentation:** https://docs.tradelocker.com/api/
- **Base URL(s):** 
  - Production: `https://api.tradelocker.com/v2`
  - WebSocket: `wss://api.tradelocker.com/ws`
- **Authentication:** OAuth2 with JWT tokens, automatic refresh
- **Rate Limits:** 100 requests/second for REST, unlimited WebSocket connections

**Key Endpoints Used:**
- `POST /auth/token` - OAuth2 authentication
- `POST /orders` - Place market/limit/stop orders
- `PUT /orders/{id}` - Modify existing orders
- `DELETE /orders/{id}` - Cancel orders
- `GET /positions` - Current positions
- `GET /account/balance` - Account balance and equity
- `WebSocket /ws` - Real-time price and position updates

**Integration Notes:** Modern REST API with excellent documentation. WebSocket provides real-time updates with <10ms latency. Supports multiple accounts per API key. Implement token refresh 5 minutes before expiration.

## DXtrade API

- **Purpose:** Trade execution via FIX protocol, position management, multi-session support
- **Documentation:** DXtrade FIX 4.4 Specification (proprietary)
- **Base URL(s):** 
  - FIX Gateway: `fix.dxtrade.com:443`
  - REST API: `https://api.dxtrade.com/v2`
- **Authentication:** SSL certificate-based for FIX, API key for REST
- **Rate Limits:** No hard limits on FIX, 50 requests/second for REST

**Key Endpoints Used:**
- FIX `NewOrderSingle` - Place orders
- FIX `OrderCancelRequest` - Cancel orders
- FIX `OrderCancelReplaceRequest` - Modify orders
- FIX `ExecutionReport` - Order status updates
- REST `GET /account` - Account information
- REST `GET /symbols` - Available instruments

**Integration Notes:** FIX 4.4 protocol for trading, REST for account queries. Requires SSL certificates for authentication. Implement sequence number persistence and gap fill. Session times configured per prop firm requirements.

## Economic Calendar API (Trading Economics)

- **Purpose:** News event filtering for trading restrictions during high-impact announcements
- **Documentation:** https://docs.tradingeconomics.com/
- **Base URL(s):** `https://api.tradingeconomics.com`
- **Authentication:** API key via query parameter
- **Rate Limits:** 500 requests/month (free tier)

**Key Endpoints Used:**
- `GET /calendar` - Economic events calendar
- `GET /calendar/country/{country}` - Country-specific events
- `GET /calendar/indicator/{indicator}` - Specific indicator data

**Integration Notes:** Used by risk management for news trading restrictions. Cache events daily to minimize API calls. Filter for high-impact events affecting traded currencies.

## HashiCorp Vault API

- **Purpose:** Secure storage and rotation of API keys, broker credentials, and sensitive configuration
- **Documentation:** https://developer.hashicorp.com/vault/api-docs
- **Base URL(s):** Self-hosted Vault instance
- **Authentication:** Vault token or Kubernetes service account
- **Rate Limits:** No enforced limits (self-hosted)

**Key Endpoints Used:**
- `GET /v1/secret/data/{path}` - Retrieve secrets
- `POST /v1/secret/data/{path}` - Store secrets
- `POST /v1/auth/kubernetes/login` - Kubernetes authentication
- `GET /v1/sys/health` - Health check

**Integration Notes:** Critical for security compliance. All external API credentials stored here. Implement automatic token renewal. Use Kubernetes service accounts for pod authentication.
