"""
Tax Reporting System - Story 8.15

Handles tax reporting requirements including:
- Form 1099 generation
- Wash sale rule tracking
- Cost basis calculations
- Tax-adjusted P&L reports
- Tax document export
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import csv
from collections import defaultdict
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)


class TaxReportType(Enum):
    """Types of tax reports"""
    FORM_1099 = "form_1099"
    FORM_1099_B = "form_1099_b"
    FORM_1099_INT = "form_1099_int"
    FORM_1099_DIV = "form_1099_div"
    FORM_8949 = "form_8949"
    SCHEDULE_D = "schedule_d"
    WASH_SALE_REPORT = "wash_sale_report"
    COST_BASIS_SUMMARY = "cost_basis_summary"


class CostBasisMethod(Enum):
    """Cost basis calculation methods"""
    FIFO = "fifo"  # First In, First Out
    LIFO = "lifo"  # Last In, First Out
    HIFO = "hifo"  # Highest In, First Out
    SPECIFIC_ID = "specific_id"  # Specific Identification
    AVERAGE_COST = "average_cost"  # Average Cost


class TransactionType(Enum):
    """Types of taxable transactions"""
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    SHORT_SALE = "short_sale"
    COVER_SHORT = "cover_short"
    OPTION_EXERCISE = "option_exercise"
    OPTION_ASSIGNMENT = "option_assignment"


@dataclass
class TaxableTransaction:
    """Represents a taxable transaction"""
    transaction_id: str
    account_id: str
    instrument: str
    transaction_type: TransactionType
    transaction_date: datetime
    settlement_date: datetime
    quantity: Decimal
    price: Decimal
    total_amount: Decimal
    commission: Decimal
    fees: Decimal
    cost_basis: Optional[Decimal] = None
    proceeds: Optional[Decimal] = None
    realized_gain_loss: Optional[Decimal] = None
    wash_sale_loss_disallowed: Optional[Decimal] = None
    wash_sale_adjustment: Optional[Decimal] = None
    holding_period_days: Optional[int] = None
    is_long_term: Optional[bool] = None
    tax_lot_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WashSaleViolation:
    """Represents a wash sale violation"""
    violation_id: str
    account_id: str
    instrument: str
    sale_date: datetime
    sale_transaction_id: str
    repurchase_date: datetime
    repurchase_transaction_id: str
    loss_amount: Decimal
    disallowed_loss: Decimal
    adjusted_cost_basis: Decimal
    violation_window_start: datetime
    violation_window_end: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaxLot:
    """Represents a tax lot for cost basis tracking"""
    lot_id: str
    account_id: str
    instrument: str
    acquisition_date: datetime
    quantity: Decimal
    remaining_quantity: Decimal
    cost_per_unit: Decimal
    total_cost: Decimal
    adjusted_cost_basis: Decimal
    wash_sale_adjustment: Decimal = Decimal('0')
    is_closed: bool = False
    closing_transactions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Form1099Data:
    """Data structure for Form 1099 reporting"""
    tax_year: int
    account_id: str
    taxpayer_id: str
    taxpayer_name: str
    taxpayer_address: str
    broker_name: str
    broker_id: str
    
    # 1099-B data
    total_proceeds: Decimal = Decimal('0')
    total_cost_basis: Decimal = Decimal('0')
    total_wash_sale_disallowed: Decimal = Decimal('0')
    short_term_gain_loss: Decimal = Decimal('0')
    long_term_gain_loss: Decimal = Decimal('0')
    
    # 1099-INT data
    interest_income: Decimal = Decimal('0')
    tax_exempt_interest: Decimal = Decimal('0')
    
    # 1099-DIV data
    ordinary_dividends: Decimal = Decimal('0')
    qualified_dividends: Decimal = Decimal('0')
    
    transactions: List[TaxableTransaction] = field(default_factory=list)
    wash_sales: List[WashSaleViolation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaxReportingSystem:
    """Main tax reporting system"""
    
    def __init__(self):
        self.transactions: Dict[str, List[TaxableTransaction]] = defaultdict(list)
        self.tax_lots: Dict[str, List[TaxLot]] = defaultdict(list)
        self.wash_sales: Dict[str, List[WashSaleViolation]] = defaultdict(list)
        self.form_1099_data: Dict[str, Dict[int, Form1099Data]] = defaultdict(dict)
        self.cost_basis_method = CostBasisMethod.FIFO
        self.wash_sale_tracker = WashSaleTracker()
        self.cost_basis_calculator = CostBasisCalculator()
        self.tax_document_generator = TaxDocumentGenerator()
        
    async def initialize(self):
        """Initialize tax reporting system"""
        logger.info("Initializing tax reporting system")
        await self.wash_sale_tracker.initialize()
        await self.cost_basis_calculator.initialize()
        await self.tax_document_generator.initialize()
        
    async def record_transaction(self, transaction: TaxableTransaction):
        """Record a taxable transaction"""
        account_id = transaction.account_id
        self.transactions[account_id].append(transaction)
        
        # Update tax lots for buy transactions
        if transaction.transaction_type in [TransactionType.BUY, TransactionType.COVER_SHORT]:
            await self._create_tax_lot(transaction)
        
        # Calculate cost basis and gain/loss for sell transactions
        if transaction.transaction_type in [TransactionType.SELL, TransactionType.SHORT_SALE]:
            await self._process_sale_transaction(transaction)
        
        # Check for wash sale violations
        if transaction.realized_gain_loss and transaction.realized_gain_loss < 0:
            wash_sale = await self.wash_sale_tracker.check_wash_sale(
                transaction, self.transactions[account_id]
            )
            if wash_sale:
                self.wash_sales[account_id].append(wash_sale)
                await self._apply_wash_sale_adjustment(transaction, wash_sale)
        
        logger.info(f"Recorded transaction: {transaction.transaction_id}")
        
    async def _create_tax_lot(self, transaction: TaxableTransaction):
        """Create a new tax lot from buy transaction"""
        tax_lot = TaxLot(
            lot_id=f"lot_{transaction.transaction_id}",
            account_id=transaction.account_id,
            instrument=transaction.instrument,
            acquisition_date=transaction.transaction_date,
            quantity=transaction.quantity,
            remaining_quantity=transaction.quantity,
            cost_per_unit=transaction.price,
            total_cost=transaction.total_amount,
            adjusted_cost_basis=transaction.total_amount + transaction.commission + transaction.fees
        )
        
        self.tax_lots[transaction.account_id].append(tax_lot)
        
    async def _process_sale_transaction(self, transaction: TaxableTransaction):
        """Process sale transaction and calculate gain/loss"""
        # Get matching tax lots based on cost basis method
        matching_lots = await self.cost_basis_calculator.get_matching_lots(
            transaction,
            self.tax_lots[transaction.account_id],
            self.cost_basis_method
        )
        
        total_cost_basis = Decimal('0')
        total_proceeds = transaction.total_amount - transaction.commission - transaction.fees
        
        for lot, quantity_used in matching_lots:
            # Calculate cost basis for this portion
            lot_cost_basis = (lot.adjusted_cost_basis / lot.quantity) * quantity_used
            total_cost_basis += lot_cost_basis
            
            # Update lot remaining quantity
            lot.remaining_quantity -= quantity_used
            if lot.remaining_quantity == 0:
                lot.is_closed = True
            lot.closing_transactions.append(transaction.transaction_id)
            
            # Calculate holding period
            holding_period = (transaction.transaction_date - lot.acquisition_date).days
            transaction.holding_period_days = holding_period
            transaction.is_long_term = holding_period > 365
        
        # Set transaction cost basis and gain/loss
        transaction.cost_basis = total_cost_basis
        transaction.proceeds = total_proceeds
        transaction.realized_gain_loss = total_proceeds - total_cost_basis
        
    async def _apply_wash_sale_adjustment(self, transaction: TaxableTransaction, 
                                          wash_sale: WashSaleViolation):
        """Apply wash sale adjustments to transaction and tax lots"""
        # Disallow the loss
        transaction.wash_sale_loss_disallowed = wash_sale.disallowed_loss
        transaction.realized_gain_loss += wash_sale.disallowed_loss  # Add back disallowed loss
        
        # Adjust cost basis of repurchase lots
        repurchase_lots = [
            lot for lot in self.tax_lots[transaction.account_id]
            if lot.acquisition_date >= wash_sale.violation_window_start
            and lot.acquisition_date <= wash_sale.violation_window_end
            and lot.instrument == transaction.instrument
        ]
        
        if repurchase_lots:
            adjustment_per_lot = wash_sale.disallowed_loss / len(repurchase_lots)
            for lot in repurchase_lots:
                lot.wash_sale_adjustment += adjustment_per_lot
                lot.adjusted_cost_basis += adjustment_per_lot
        
    async def generate_form_1099(self, account_id: str, tax_year: int,
                                 taxpayer_info: Dict[str, str]) -> Form1099Data:
        """Generate Form 1099 data for an account"""
        form_data = Form1099Data(
            tax_year=tax_year,
            account_id=account_id,
            taxpayer_id=taxpayer_info.get('taxpayer_id', ''),
            taxpayer_name=taxpayer_info.get('name', ''),
            taxpayer_address=taxpayer_info.get('address', ''),
            broker_name=taxpayer_info.get('broker_name', 'Trading Platform'),
            broker_id=taxpayer_info.get('broker_id', '')
        )
        
        # Get all transactions for the tax year
        year_transactions = [
            t for t in self.transactions[account_id]
            if t.transaction_date.year == tax_year
        ]
        
        # Process transactions by type
        for transaction in year_transactions:
            if transaction.transaction_type in [TransactionType.SELL, TransactionType.COVER_SHORT]:
                form_data.total_proceeds += transaction.proceeds or Decimal('0')
                form_data.total_cost_basis += transaction.cost_basis or Decimal('0')
                form_data.total_wash_sale_disallowed += transaction.wash_sale_loss_disallowed or Decimal('0')
                
                if transaction.realized_gain_loss:
                    if transaction.is_long_term:
                        form_data.long_term_gain_loss += transaction.realized_gain_loss
                    else:
                        form_data.short_term_gain_loss += transaction.realized_gain_loss
                        
            elif transaction.transaction_type == TransactionType.DIVIDEND:
                form_data.ordinary_dividends += transaction.total_amount
                # Check if qualified (simplified - would need more logic in production)
                if transaction.metadata.get('is_qualified'):
                    form_data.qualified_dividends += transaction.total_amount
                    
            elif transaction.transaction_type == TransactionType.INTEREST:
                form_data.interest_income += transaction.total_amount
                if transaction.metadata.get('is_tax_exempt'):
                    form_data.tax_exempt_interest += transaction.total_amount
        
        form_data.transactions = year_transactions
        form_data.wash_sales = [
            ws for ws in self.wash_sales[account_id]
            if ws.sale_date.year == tax_year
        ]
        
        self.form_1099_data[account_id][tax_year] = form_data
        
        return form_data
        
    async def export_tax_documents(self, account_id: str, tax_year: int,
                                   output_dir: Path) -> Dict[str, Path]:
        """Export all tax documents for an account"""
        if account_id not in self.form_1099_data or tax_year not in self.form_1099_data[account_id]:
            raise ValueError(f"No tax data for account {account_id} year {tax_year}")
        
        form_data = self.form_1099_data[account_id][tax_year]
        
        # Generate various tax documents
        documents = {}
        
        # Form 1099-B
        documents['1099-B'] = await self.tax_document_generator.generate_1099b(
            form_data, output_dir
        )
        
        # Form 8949
        documents['8949'] = await self.tax_document_generator.generate_8949(
            form_data, output_dir
        )
        
        # Wash sale report
        if form_data.wash_sales:
            documents['wash_sales'] = await self.tax_document_generator.generate_wash_sale_report(
                form_data, output_dir
            )
        
        # Cost basis summary
        documents['cost_basis'] = await self.tax_document_generator.generate_cost_basis_summary(
            self.tax_lots[account_id], tax_year, output_dir
        )
        
        return documents
        
    async def get_tax_summary(self, account_id: str, tax_year: int) -> Dict[str, Any]:
        """Get tax summary for an account"""
        if account_id not in self.form_1099_data or tax_year not in self.form_1099_data[account_id]:
            return {}
        
        form_data = self.form_1099_data[account_id][tax_year]
        
        return {
            'tax_year': tax_year,
            'account_id': account_id,
            'total_proceeds': float(form_data.total_proceeds),
            'total_cost_basis': float(form_data.total_cost_basis),
            'net_gain_loss': float(form_data.total_proceeds - form_data.total_cost_basis),
            'short_term_gain_loss': float(form_data.short_term_gain_loss),
            'long_term_gain_loss': float(form_data.long_term_gain_loss),
            'wash_sale_disallowed': float(form_data.total_wash_sale_disallowed),
            'interest_income': float(form_data.interest_income),
            'dividend_income': float(form_data.ordinary_dividends),
            'qualified_dividends': float(form_data.qualified_dividends),
            'transaction_count': len(form_data.transactions),
            'wash_sale_count': len(form_data.wash_sales)
        }


class WashSaleTracker:
    """Tracks and identifies wash sale violations"""
    
    def __init__(self):
        self.wash_sale_window = 30  # 30 days before and after
        self.violations: List[WashSaleViolation] = []
        
    async def initialize(self):
        """Initialize wash sale tracker"""
        logger.info("Initialized wash sale tracker")
        
    async def check_wash_sale(self, sale_transaction: TaxableTransaction,
                              all_transactions: List[TaxableTransaction]) -> Optional[WashSaleViolation]:
        """Check if a sale transaction violates wash sale rules"""
        if not sale_transaction.realized_gain_loss or sale_transaction.realized_gain_loss >= 0:
            return None  # No loss, no wash sale
        
        window_start = sale_transaction.transaction_date - timedelta(days=self.wash_sale_window)
        window_end = sale_transaction.transaction_date + timedelta(days=self.wash_sale_window)
        
        # Look for repurchases of substantially identical securities
        repurchases = [
            t for t in all_transactions
            if t.instrument == sale_transaction.instrument
            and t.transaction_type in [TransactionType.BUY, TransactionType.COVER_SHORT]
            and window_start <= t.transaction_date <= window_end
            and t.transaction_id != sale_transaction.transaction_id
        ]
        
        if not repurchases:
            return None
        
        # Create wash sale violation
        earliest_repurchase = min(repurchases, key=lambda x: x.transaction_date)
        
        violation = WashSaleViolation(
            violation_id=f"ws_{sale_transaction.transaction_id}",
            account_id=sale_transaction.account_id,
            instrument=sale_transaction.instrument,
            sale_date=sale_transaction.transaction_date,
            sale_transaction_id=sale_transaction.transaction_id,
            repurchase_date=earliest_repurchase.transaction_date,
            repurchase_transaction_id=earliest_repurchase.transaction_id,
            loss_amount=abs(sale_transaction.realized_gain_loss),
            disallowed_loss=abs(sale_transaction.realized_gain_loss),
            adjusted_cost_basis=earliest_repurchase.total_amount + abs(sale_transaction.realized_gain_loss),
            violation_window_start=window_start,
            violation_window_end=window_end
        )
        
        self.violations.append(violation)
        logger.warning(f"Wash sale violation detected: {violation.violation_id}")
        
        return violation


class CostBasisCalculator:
    """Calculates cost basis using various methods"""
    
    def __init__(self):
        self.methods = {
            CostBasisMethod.FIFO: self._fifo_matching,
            CostBasisMethod.LIFO: self._lifo_matching,
            CostBasisMethod.HIFO: self._hifo_matching,
            CostBasisMethod.SPECIFIC_ID: self._specific_id_matching,
            CostBasisMethod.AVERAGE_COST: self._average_cost_matching
        }
        
    async def initialize(self):
        """Initialize cost basis calculator"""
        logger.info("Initialized cost basis calculator")
        
    async def get_matching_lots(self, sale_transaction: TaxableTransaction,
                                tax_lots: List[TaxLot],
                                method: CostBasisMethod) -> List[Tuple[TaxLot, Decimal]]:
        """Get matching tax lots for a sale using specified method"""
        matching_func = self.methods.get(method, self._fifo_matching)
        return await matching_func(sale_transaction, tax_lots)
        
    async def _fifo_matching(self, sale_transaction: TaxableTransaction,
                             tax_lots: List[TaxLot]) -> List[Tuple[TaxLot, Decimal]]:
        """Match tax lots using FIFO method"""
        eligible_lots = [
            lot for lot in sorted(tax_lots, key=lambda x: x.acquisition_date)
            if lot.instrument == sale_transaction.instrument
            and lot.remaining_quantity > 0
        ]
        
        return await self._match_lots_to_quantity(sale_transaction.quantity, eligible_lots)
        
    async def _lifo_matching(self, sale_transaction: TaxableTransaction,
                             tax_lots: List[TaxLot]) -> List[Tuple[TaxLot, Decimal]]:
        """Match tax lots using LIFO method"""
        eligible_lots = [
            lot for lot in sorted(tax_lots, key=lambda x: x.acquisition_date, reverse=True)
            if lot.instrument == sale_transaction.instrument
            and lot.remaining_quantity > 0
        ]
        
        return await self._match_lots_to_quantity(sale_transaction.quantity, eligible_lots)
        
    async def _hifo_matching(self, sale_transaction: TaxableTransaction,
                             tax_lots: List[TaxLot]) -> List[Tuple[TaxLot, Decimal]]:
        """Match tax lots using HIFO method (highest cost first)"""
        eligible_lots = [
            lot for lot in sorted(tax_lots, key=lambda x: x.cost_per_unit, reverse=True)
            if lot.instrument == sale_transaction.instrument
            and lot.remaining_quantity > 0
        ]
        
        return await self._match_lots_to_quantity(sale_transaction.quantity, eligible_lots)
        
    async def _specific_id_matching(self, sale_transaction: TaxableTransaction,
                                    tax_lots: List[TaxLot]) -> List[Tuple[TaxLot, Decimal]]:
        """Match specific tax lots (requires lot IDs in transaction metadata)"""
        specified_lot_ids = sale_transaction.metadata.get('specified_lots', [])
        
        if not specified_lot_ids:
            # Fall back to FIFO if no specific lots specified
            return await self._fifo_matching(sale_transaction, tax_lots)
        
        eligible_lots = [
            lot for lot in tax_lots
            if lot.lot_id in specified_lot_ids
            and lot.instrument == sale_transaction.instrument
            and lot.remaining_quantity > 0
        ]
        
        return await self._match_lots_to_quantity(sale_transaction.quantity, eligible_lots)
        
    async def _average_cost_matching(self, sale_transaction: TaxableTransaction,
                                     tax_lots: List[TaxLot]) -> List[Tuple[TaxLot, Decimal]]:
        """Match using average cost method"""
        eligible_lots = [
            lot for lot in tax_lots
            if lot.instrument == sale_transaction.instrument
            and lot.remaining_quantity > 0
        ]
        
        if not eligible_lots:
            return []
        
        # Calculate average cost
        total_quantity = sum(lot.remaining_quantity for lot in eligible_lots)
        total_cost = sum(lot.adjusted_cost_basis * (lot.remaining_quantity / lot.quantity) 
                        for lot in eligible_lots)
        avg_cost_per_unit = total_cost / total_quantity if total_quantity > 0 else Decimal('0')
        
        # Create synthetic average lot
        avg_lot = TaxLot(
            lot_id="avg_lot",
            account_id=sale_transaction.account_id,
            instrument=sale_transaction.instrument,
            acquisition_date=min(lot.acquisition_date for lot in eligible_lots),
            quantity=total_quantity,
            remaining_quantity=total_quantity,
            cost_per_unit=avg_cost_per_unit,
            total_cost=total_cost,
            adjusted_cost_basis=total_cost
        )
        
        return [(avg_lot, min(sale_transaction.quantity, total_quantity))]
        
    async def _match_lots_to_quantity(self, needed_quantity: Decimal,
                                      eligible_lots: List[TaxLot]) -> List[Tuple[TaxLot, Decimal]]:
        """Match lots to fulfill needed quantity"""
        matched_lots = []
        remaining_needed = needed_quantity
        
        for lot in eligible_lots:
            if remaining_needed <= 0:
                break
                
            quantity_from_lot = min(lot.remaining_quantity, remaining_needed)
            matched_lots.append((lot, quantity_from_lot))
            remaining_needed -= quantity_from_lot
            
        return matched_lots


class TaxDocumentGenerator:
    """Generates tax documents and reports"""
    
    def __init__(self):
        self.templates = {}
        
    async def initialize(self):
        """Initialize document generator"""
        logger.info("Initialized tax document generator")
        
    async def generate_1099b(self, form_data: Form1099Data, output_dir: Path) -> Path:
        """Generate Form 1099-B"""
        output_file = output_dir / f"1099B_{form_data.account_id}_{form_data.tax_year}.csv"
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['Form 1099-B - Proceeds From Broker and Barter Exchange Transactions'])
            writer.writerow([f'Tax Year: {form_data.tax_year}'])
            writer.writerow([f'Account: {form_data.account_id}'])
            writer.writerow([f'Taxpayer: {form_data.taxpayer_name}'])
            writer.writerow([])
            
            # Transaction details
            writer.writerow([
                'Date Sold', 'Date Acquired', 'Security', 'Quantity',
                'Proceeds', 'Cost Basis', 'Gain/Loss', 'Term', 'Wash Sale'
            ])
            
            for t in form_data.transactions:
                if t.transaction_type in [TransactionType.SELL, TransactionType.COVER_SHORT]:
                    writer.writerow([
                        t.transaction_date.strftime('%Y-%m-%d'),
                        t.metadata.get('acquisition_date', ''),
                        t.instrument,
                        float(t.quantity),
                        float(t.proceeds or 0),
                        float(t.cost_basis or 0),
                        float(t.realized_gain_loss or 0),
                        'LT' if t.is_long_term else 'ST',
                        float(t.wash_sale_loss_disallowed or 0)
                    ])
            
            # Summary
            writer.writerow([])
            writer.writerow(['Summary:'])
            writer.writerow([f'Total Proceeds: ${float(form_data.total_proceeds):,.2f}'])
            writer.writerow([f'Total Cost Basis: ${float(form_data.total_cost_basis):,.2f}'])
            writer.writerow([f'Total Gain/Loss: ${float(form_data.total_proceeds - form_data.total_cost_basis):,.2f}'])
            writer.writerow([f'Wash Sale Disallowed: ${float(form_data.total_wash_sale_disallowed):,.2f}'])
            
        logger.info(f"Generated 1099-B: {output_file}")
        return output_file
        
    async def generate_8949(self, form_data: Form1099Data, output_dir: Path) -> Path:
        """Generate Form 8949"""
        output_file = output_dir / f"8949_{form_data.account_id}_{form_data.tax_year}.csv"
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['Form 8949 - Sales and Other Dispositions of Capital Assets'])
            writer.writerow([f'Tax Year: {form_data.tax_year}'])
            writer.writerow([f'Account: {form_data.account_id}'])
            writer.writerow([])
            
            # Part I - Short Term
            writer.writerow(['Part I - Short-Term Capital Gains and Losses'])
            writer.writerow([
                'Description', 'Date Acquired', 'Date Sold', 'Proceeds',
                'Cost Basis', 'Adjustment', 'Gain/Loss'
            ])
            
            short_term_total = Decimal('0')
            for t in form_data.transactions:
                if t.transaction_type in [TransactionType.SELL, TransactionType.COVER_SHORT]:
                    if not t.is_long_term:
                        adjustment = t.wash_sale_loss_disallowed or Decimal('0')
                        writer.writerow([
                            f"{t.quantity} {t.instrument}",
                            t.metadata.get('acquisition_date', ''),
                            t.transaction_date.strftime('%Y-%m-%d'),
                            float(t.proceeds or 0),
                            float(t.cost_basis or 0),
                            float(adjustment),
                            float(t.realized_gain_loss or 0)
                        ])
                        short_term_total += t.realized_gain_loss or Decimal('0')
            
            writer.writerow(['', '', '', '', '', 'Total:', float(short_term_total)])
            writer.writerow([])
            
            # Part II - Long Term
            writer.writerow(['Part II - Long-Term Capital Gains and Losses'])
            writer.writerow([
                'Description', 'Date Acquired', 'Date Sold', 'Proceeds',
                'Cost Basis', 'Adjustment', 'Gain/Loss'
            ])
            
            long_term_total = Decimal('0')
            for t in form_data.transactions:
                if t.transaction_type in [TransactionType.SELL, TransactionType.COVER_SHORT]:
                    if t.is_long_term:
                        adjustment = t.wash_sale_loss_disallowed or Decimal('0')
                        writer.writerow([
                            f"{t.quantity} {t.instrument}",
                            t.metadata.get('acquisition_date', ''),
                            t.transaction_date.strftime('%Y-%m-%d'),
                            float(t.proceeds or 0),
                            float(t.cost_basis or 0),
                            float(adjustment),
                            float(t.realized_gain_loss or 0)
                        ])
                        long_term_total += t.realized_gain_loss or Decimal('0')
            
            writer.writerow(['', '', '', '', '', 'Total:', float(long_term_total)])
            
        logger.info(f"Generated Form 8949: {output_file}")
        return output_file
        
    async def generate_wash_sale_report(self, form_data: Form1099Data, output_dir: Path) -> Path:
        """Generate wash sale violation report"""
        output_file = output_dir / f"wash_sales_{form_data.account_id}_{form_data.tax_year}.csv"
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            writer.writerow(['Wash Sale Violation Report'])
            writer.writerow([f'Tax Year: {form_data.tax_year}'])
            writer.writerow([f'Account: {form_data.account_id}'])
            writer.writerow([])
            
            writer.writerow([
                'Violation ID', 'Security', 'Sale Date', 'Repurchase Date',
                'Loss Amount', 'Disallowed Loss', 'Adjusted Cost Basis'
            ])
            
            total_disallowed = Decimal('0')
            for ws in form_data.wash_sales:
                writer.writerow([
                    ws.violation_id,
                    ws.instrument,
                    ws.sale_date.strftime('%Y-%m-%d'),
                    ws.repurchase_date.strftime('%Y-%m-%d'),
                    float(ws.loss_amount),
                    float(ws.disallowed_loss),
                    float(ws.adjusted_cost_basis)
                ])
                total_disallowed += ws.disallowed_loss
            
            writer.writerow([])
            writer.writerow([f'Total Disallowed Loss: ${float(total_disallowed):,.2f}'])
            
        logger.info(f"Generated wash sale report: {output_file}")
        return output_file
        
    async def generate_cost_basis_summary(self, tax_lots: List[TaxLot], 
                                          tax_year: int, output_dir: Path) -> Path:
        """Generate cost basis summary report"""
        account_id = tax_lots[0].account_id if tax_lots else 'unknown'
        output_file = output_dir / f"cost_basis_{account_id}_{tax_year}.csv"
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            writer.writerow(['Cost Basis Summary Report'])
            writer.writerow([f'Tax Year: {tax_year}'])
            writer.writerow([])
            
            writer.writerow([
                'Lot ID', 'Security', 'Acquisition Date', 'Quantity',
                'Remaining', 'Cost/Unit', 'Total Cost', 'Adjusted Basis', 'Status'
            ])
            
            for lot in tax_lots:
                writer.writerow([
                    lot.lot_id,
                    lot.instrument,
                    lot.acquisition_date.strftime('%Y-%m-%d'),
                    float(lot.quantity),
                    float(lot.remaining_quantity),
                    float(lot.cost_per_unit),
                    float(lot.total_cost),
                    float(lot.adjusted_cost_basis),
                    'Closed' if lot.is_closed else 'Open'
                ])
            
        logger.info(f"Generated cost basis summary: {output_file}")
        return output_file