# US Regulatory Requirements

## Overview

This document outlines the comprehensive US regulatory requirements applicable to the TMT trading system, including CFTC, SEC, and FINRA regulations that govern algorithmic trading operations.

## Regulatory Framework

### Primary Regulators

#### Commodity Futures Trading Commission (CFTC)
- **Jurisdiction**: Futures and derivatives trading
- **Key Regulations**: CEA, CFTC Rules Part 1-190
- **Registration**: CPO/CTA registration if managing customer funds
- **Reporting**: Large trader reporting, swap data reporting

#### Securities and Exchange Commission (SEC)
- **Jurisdiction**: Securities trading and investment advice
- **Key Regulations**: Securities Exchange Act, Investment Advisers Act
- **Registration**: Investment adviser registration if providing advice
- **Reporting**: Form 13F, beneficial ownership reporting

#### Financial Industry Regulatory Authority (FINRA)
- **Jurisdiction**: Broker-dealer activities and market conduct
- **Key Regulations**: FINRA Rules, NASDAQ/NYSE rules
- **Registration**: Broker-dealer registration for proprietary trading
- **Reporting**: Trade reporting, order audit trail system (OATS)

### Applicable Regulations

#### Algorithmic Trading Regulations

**CFTC Rule 1.35 - Risk Controls for Trading**
- Pre-trade risk controls required
- Maximum order size limits
- Credit/capital threshold checks
- Automated position limits

**SEC Rule 15c3-5 - Market Access Rule**
- Risk management controls for electronic access
- Financial and regulatory risk management controls
- Regular review and testing of controls
- Supervisory procedures for electronic trading

**FINRA Rule 3110 - Supervision**
- Supervisory systems for algorithmic trading
- Testing and monitoring of trading systems
- Documentation of supervisory procedures
- Regular review of trading activities

## Compliance Requirements

### Registration and Licensing

#### Commodity Pool Operator (CPO) Registration
**Trigger**: Managing futures trading for multiple participants
**Requirements**:
- CFTC registration and NFA membership
- Disclosure document filing
- Recordkeeping and reporting obligations
- Capital and segregation requirements

```yaml
cpo_requirements:
  registration: "Required if managing participant funds"
  net_capital: "$50,000 minimum"
  disclosure: "Pool disclosure document required"
  reporting: "Monthly account statements, annual reports"
  books_records: "5-year retention requirement"
```

#### Commodity Trading Advisor (CTA) Registration
**Trigger**: Providing trading advice for compensation
**Requirements**:
- CFTC registration and NFA membership
- Disclosure document preparation
- Performance reporting standards
- Client suitability determinations

#### Investment Adviser Registration
**Trigger**: Providing investment advice for compensation
**Requirements**:
- SEC or state registration (depending on AUM)
- Form ADV filing and updates
- Compliance program establishment
- Custody rule compliance if applicable

### Trading Compliance

#### Position Reporting

**CFTC Large Trader Reporting**
```yaml
large_trader_reporting:
  threshold: "25+ contracts in reportable commodities"
  frequency: "Daily by 9:00 AM CT"
  form: "Form 40 (trader identification)"
  positions: "Daily Form 103 (position report)"
```

**SEC Large Position Reporting**
```yaml
sec_reporting:
  beneficial_ownership: ">5% of any class of equity securities"
  form_13f: ">$100M equity assets under management"
  frequency: "Quarterly within 45 days"
  amendments: "Within 10 days for material changes"
```

#### Trade Reporting

**FINRA Trade Reporting**
- Real-time reporting to Trade Reporting Facility (TRF)
- Accurate trade price, volume, and time reporting
- Compliance with trade-through and locked market rules
- Audit trail maintenance (OATS/CAT reporting)

**CFTC Swap Data Reporting**
- Real-time reporting for swap transactions
- Swap data repository (SDR) reporting
- Counterparty and transaction data accuracy
- Legal entity identifier (LEI) requirements

### Risk Management Compliance

#### Pre-Trade Risk Controls
```yaml
pretrade_controls:
  order_size_limits:
    maximum_order: "Based on capital and risk limits"
    position_limits: "Regulatory and internal limits"
    concentration_limits: "Sector and instrument limits"
    
  credit_controls:
    available_capital: "Real-time capital checking"
    margin_requirements: "Margin adequacy verification"
    exposure_limits: "Gross and net exposure limits"
    
  regulatory_controls:
    position_limits: "Speculative position limit compliance"
    restricted_securities: "Restricted list checking"
    wash_sale_rules: "Wash sale prevention"
```

#### Post-Trade Compliance
- Trade surveillance and monitoring
- Exception reporting and investigation
- Regulatory reporting accuracy
- Record retention compliance

### Recordkeeping Requirements

#### Required Records

**CFTC Recordkeeping (Rule 1.35)**
```yaml
cftc_records:
  risk_controls:
    description: "Pre-trade risk control settings"
    retention: "5 years"
    
  trading_records:
    description: "All orders, modifications, cancellations"
    retention: "5 years"
    
  system_safeguards:
    description: "System safeguards and controls"
    retention: "3 years after system retirement"
    
  testing_records:
    description: "Control testing and validation"
    retention: "3 years"
```

**SEC Recordkeeping (Rule 17a-4)**
```yaml
sec_records:
  order_records:
    description: "Order tickets and trade confirmations"
    retention: "6 years (3 years readily accessible)"
    
  communications:
    description: "Business-related communications"
    retention: "3 years"
    
  financial_records:
    description: "Financial statements and computations"
    retention: "6 years"
    
  supervisory_records:
    description: "Supervisory procedures and reviews"
    retention: "3 years"
```

### Anti-Manipulation Compliance

#### Market Manipulation Prevention
```yaml
antimanipulation_controls:
  spoofing_prevention:
    description: "Controls to prevent spoofing/layering"
    implementation: "Order pattern analysis"
    monitoring: "Real-time surveillance"
    
  wash_trading_prevention:
    description: "Prevent wash sales and circular trading"
    implementation: "Account and beneficial owner checks"
    monitoring: "Cross-account transaction analysis"
    
  disruptive_practices:
    description: "Prevent disruptive trading practices"
    implementation: "Velocity and frequency controls"
    monitoring: "Anomalous trading pattern detection"
```

#### Market Surveillance
- Real-time trade surveillance systems
- Exception-based monitoring and alerting
- Investigation and reporting procedures
- Regulatory reporting of suspicious activities

## Compliance Program Requirements

### Written Supervisory Procedures (WSPs)

#### Required Elements
1. **Risk Management Procedures**
   - Pre-trade and post-trade risk controls
   - Position and concentration limits
   - System safeguards and circuit breakers

2. **Trading Supervision**
   - Algorithmic trading oversight
   - Order management procedures
   - Trade review and exception handling

3. **Regulatory Reporting**
   - Large trader reporting procedures
   - Trade reporting requirements
   - Regulatory examination procedures

4. **Recordkeeping and Retention**
   - Document retention policies
   - Electronic storage requirements
   - Audit trail maintenance

### Compliance Testing and Monitoring

#### Annual Review Requirements
```yaml
annual_review:
  risk_controls:
    description: "Review and test all risk controls"
    frequency: "Annual minimum"
    documentation: "Testing results and remediation"
    
  supervisory_procedures:
    description: "Review adequacy of WSPs"
    frequency: "Annual"
    updates: "Modify procedures as needed"
    
  training_programs:
    description: "Review training effectiveness"
    frequency: "Annual"
    certification: "Employee certification records"
```

#### Ongoing Monitoring
- Daily risk limit monitoring
- Exception reporting and resolution
- System performance monitoring
- Regulatory change impact assessment

### Training and Certification

#### Required Training Programs
```yaml
training_requirements:
  regulatory_training:
    topics: ["Market conduct", "Manipulation", "Reporting"]
    frequency: "Annual"
    certification: "Required"
    
  system_training:
    topics: ["Risk controls", "System operation", "Emergency procedures"]
    frequency: "System updates + annual"
    certification: "Required"
    
  compliance_training:
    topics: ["Procedures", "Escalation", "Investigation"]
    frequency: "Semi-annual"
    certification: "Required"
```

## Regulatory Reporting

### Automated Reporting Systems

#### CFTC Reporting
```python
class CFTCReporter:
    def __init__(self):
        self.large_trader_threshold = 25
        self.reporting_deadline = "09:00 CT"
        
    def generate_form_103(self, positions, report_date):
        """Generate daily large trader position report"""
        reportable_positions = self.filter_reportable_positions(positions)
        
        report = {
            'report_date': report_date,
            'reporting_firm': self.firm_info,
            'positions': []
        }
        
        for position in reportable_positions:
            if position['quantity'] >= self.large_trader_threshold:
                report['positions'].append({
                    'commodity': position['commodity'],
                    'contract_month': position['contract_month'],
                    'long_positions': position['long_quantity'],
                    'short_positions': position['short_quantity'],
                    'spread_positions': position['spread_quantity']
                })
        
        return self.submit_cftc_report(report)
```

#### SEC Reporting
```python
class SECReporter:
    def __init__(self):
        self.form_13f_threshold = 100000000  # $100M AUM
        self.beneficial_ownership_threshold = 0.05  # 5%
        
    def generate_form_13f(self, holdings, quarter_end):
        """Generate quarterly Form 13F report"""
        if self.calculate_total_aum(holdings) >= self.form_13f_threshold:
            
            report = {
                'report_date': quarter_end,
                'institution_info': self.institution_info,
                'holdings': []
            }
            
            for holding in holdings:
                if holding['value'] >= 200000:  # $200K minimum
                    report['holdings'].append({
                        'cusip': holding['cusip'],
                        'security_name': holding['name'],
                        'shares': holding['shares'],
                        'market_value': holding['value'],
                        'voting_authority': holding['voting_rights']
                    })
            
            return self.submit_sec_report(report)
```

### Regulatory Examination Procedures

#### Examination Preparation
1. **Document Organization**
   - Organize all required records
   - Prepare examination response team
   - Review recent compliance issues
   - Update examination procedures

2. **Data Production**
   - Electronic data production capabilities
   - Trade reconstruction capabilities
   - Communication records availability
   - System documentation completeness

#### Examination Response
- Designated examination coordinator
- Document production procedures
- Staff interview preparation
- Issue remediation procedures

## Penalties and Enforcement

### Violation Categories

#### Regulatory Violations
- Registration violations: Fines up to $1M+ per violation
- Reporting violations: Fines up to $250K per violation
- Risk control violations: Fines up to $500K per violation
- Manipulation violations: Criminal and civil penalties

#### Enforcement Actions
- Cease and desist orders
- Civil monetary penalties
- Criminal referrals
- Business suspension or revocation

### Compliance Cost Management

#### Cost Categories
```yaml
compliance_costs:
  registration_fees:
    cftc_nfa: "$5,000 - $50,000 annually"
    sec: "$150 - $16,800 annually (AUM based)"
    
  reporting_systems:
    implementation: "$50,000 - $500,000"
    ongoing_costs: "$10,000 - $100,000 annually"
    
  compliance_staff:
    cco_salary: "$150,000 - $300,000 annually"
    compliance_staff: "$75,000 - $150,000 per person"
    
  legal_advisory:
    regulatory_counsel: "$500 - $1,000 per hour"
    ongoing_advisory: "$25,000 - $100,000 annually"
```

For EU regulatory requirements, see [EU Requirements](eu-requirements.md). For international compliance, see [International Standards](international.md).