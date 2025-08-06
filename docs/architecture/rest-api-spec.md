# REST API Spec

```yaml
openapi: 3.0.0
info:
  title: Adaptive Trading System API
  version: 1.0.0
  description: REST API for the autonomous trading system supporting multi-agent coordination, account management, and real-time trading operations
servers:
  - url: https://api.trading-system.com/v1
    description: Production API server
  - url: https://staging-api.trading-system.com/v1
    description: Staging API server

security:
  - BearerAuth: []

paths:
  # Authentication endpoints
  /auth/login:
    post:
      summary: Authenticate user with 2FA
      tags: [Authentication]
      security: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [username, password, totp_code]
              properties:
                username:
                  type: string
                password:
                  type: string
                totp_code:
                  type: string
                  description: Time-based one-time password
      responses:
        '200':
          description: Login successful
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  refresh_token:
                    type: string
                  expires_in:
                    type: integer

  # Account management
  /accounts:
    get:
      summary: List all trading accounts
      tags: [Accounts]
      responses:
        '200':
          description: List of trading accounts
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/TradingAccount'
    
    post:
      summary: Create new trading account
      tags: [Accounts]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateAccountRequest'
      responses:
        '201':
          description: Account created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TradingAccount'

  /accounts/{account_id}:
    get:
      summary: Get specific account details
      tags: [Accounts]
      parameters:
        - name: account_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Account details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TradingAccount'

  # Position management  
  /accounts/{account_id}/positions:
    get:
      summary: Get account positions
      tags: [Positions]
      parameters:
        - name: account_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: status
          in: query
          schema:
            type: string
            enum: [open, closed, partial]
      responses:
        '200':
          description: List of positions
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Position'

  # Circuit breaker controls
  /breaker/status:
    get:
      summary: Get circuit breaker status
      tags: [Circuit Breaker]
      responses:
        '200':
          description: Breaker status for all levels
          content:
            application/json:
              schema:
                type: object
                properties:
                  system_level:
                    $ref: '#/components/schemas/BreakerStatus'
                  account_level:
                    type: array
                    items:
                      type: object
                      properties:
                        account_id:
                          type: string
                          format: uuid
                        status:
                          $ref: '#/components/schemas/BreakerStatus'

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    TradingAccount:
      type: object
      properties:
        account_id:
          type: string
          format: uuid
        prop_firm:
          type: string
          enum: [FTMO, MyForexFunds, FundedNext]
        account_number:
          type: string
        status:
          type: string
          enum: [active, suspended, in_drawdown, terminated]
        balance:
          type: number
          format: decimal
        equity:
          type: number
          format: decimal

    Position:
      type: object
      properties:
        position_id:
          type: string
          format: uuid
        account_id:
          type: string
          format: uuid
        symbol:
          type: string
        position_type:
          type: string
          enum: [long, short]
        volume:
          type: number
          format: decimal

    BreakerStatus:
      type: object
      properties:
        status:
          type: string
          enum: [normal, warning, tripped]
        triggered_at:
          type: string
          format: date-time
          nullable: true
        reason:
          type: string
          nullable: true
```
