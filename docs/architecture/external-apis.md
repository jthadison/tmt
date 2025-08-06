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

## MetaTrader 4/5 Bridge APIs

- **Purpose:** Direct trade execution on prop firm accounts, position management, account synchronization
- **Documentation:** Custom bridge implementation required (no standard API)
- **Base URL(s):** Local bridge service endpoints (bridge runs on same VPS as MT4/5)
- **Authentication:** Account credentials + bridge authentication token
- **Rate Limits:** Platform dependent, typically 10-20 orders/second maximum

**Key Endpoints Used:**
- `POST /bridge/order/market` - Place market orders
- `POST /bridge/order/pending` - Place pending orders
- `PUT /bridge/order/modify` - Modify stop loss/take profit
- `GET /bridge/account/info` - Account balance and equity
- `GET /bridge/positions` - Current open positions
- `WebSocket /bridge/events` - Real-time order events

**Integration Notes:** Most critical integration for execution. Requires custom bridge development. Implement connection monitoring with auto-reconnect. Handle order rejections and partial fills gracefully.

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
