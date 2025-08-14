"""
Account and trading data fixtures for testing
"""
from datetime import datetime, timedelta
from typing import Dict, List
import random
from uuid import uuid4


def generate_prop_firm_account(
    firm_name: str = "FTMO",
    account_type: str = "challenge",
    balance: float = 50000.0
) -> Dict:
    """Generate realistic prop firm account configuration"""
    
    firm_configs = {
        "FTMO": {
            "max_drawdown": 0.10,
            "daily_loss_limit": 0.05,
            "min_trading_days": 10,
            "profit_target": 0.10,
            "max_lot_size": 2.0,
            "news_trading": False,
            "weekend_holding": False,
            "platforms": ["MT4", "MT5"]
        },
        "MyForexFunds": {
            "max_drawdown": 0.12,
            "daily_loss_limit": 0.05,
            "min_trading_days": 5,
            "profit_target": 0.08,
            "max_lot_size": 1.0,
            "news_trading": True,
            "weekend_holding": True,
            "platforms": ["MT4", "MT5", "DXTrade"]
        },
        "FundedNext": {
            "max_drawdown": 0.08,
            "daily_loss_limit": 0.04,
            "min_trading_days": 5,
            "profit_target": 0.06,
            "max_lot_size": 1.5,
            "news_trading": True,
            "weekend_holding": False,
            "platforms": ["MT5"]
        }
    }
    
    config = firm_configs.get(firm_name, firm_configs["FTMO"])
    
    return {
        "account_id": f"{firm_name}_{random.randint(100000, 999999)}",
        "firm_name": firm_name,
        "account_type": account_type,  # challenge, verification, funded
        "balance": balance,
        "equity": balance,
        "free_margin": balance,
        "margin_level": 100.0,
        "platform": random.choice(config["platforms"]),
        "server": f"{firm_name.lower()}-server-01",
        "currency": "USD",
        "leverage": random.choice([1, 10, 30, 50, 100]),
        
        # Firm-specific rules
        "rules": {
            "max_drawdown_percent": config["max_drawdown"],
            "daily_loss_limit_percent": config["daily_loss_limit"],
            "min_trading_days": config["min_trading_days"],
            "profit_target_percent": config["profit_target"],
            "max_lot_size": config["max_lot_size"],
            "news_trading_allowed": config["news_trading"],
            "weekend_holding_allowed": config["weekend_holding"],
            "allowed_symbols": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "XAUUSD"],
            "restricted_times": ["news_events", "market_close"] if not config["news_trading"] else []
        },
        
        # Account status
        "status": "active",
        "created_at": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
        "last_activity": datetime.now().isoformat(),
        
        # Performance tracking
        "performance": {
            "total_trades": random.randint(50, 200),
            "winning_trades": random.randint(30, 140),
            "current_drawdown": random.uniform(0, 0.05),
            "max_drawdown": random.uniform(0.02, 0.08),
            "profit_factor": random.uniform(1.2, 2.5),
            "sharp_ratio": random.uniform(0.5, 2.0),
            "days_traded": random.randint(5, 25),
            "avg_daily_return": random.uniform(-0.002, 0.003)
        }
    }


def generate_trading_personality(risk_level: str = "moderate") -> Dict:
    """Generate trading personality configuration"""
    
    personalities = {
        "conservative": {
            "risk_per_trade": 0.005,  # 0.5%
            "max_concurrent_trades": 2,
            "preferred_timeframes": ["H4", "D1"],
            "session_preference": ["london"],
            "hold_duration": "swing",
            "news_avoidance": True,
            "volatility_tolerance": "low",
            "drawdown_sensitivity": "high"
        },
        "moderate": {
            "risk_per_trade": 0.01,   # 1%
            "max_concurrent_trades": 3,
            "preferred_timeframes": ["H1", "H4"],
            "session_preference": ["london", "newyork"],
            "hold_duration": "intraday",
            "news_avoidance": False,
            "volatility_tolerance": "medium",
            "drawdown_sensitivity": "medium"
        },
        "aggressive": {
            "risk_per_trade": 0.02,   # 2%
            "max_concurrent_trades": 5,
            "preferred_timeframes": ["M15", "H1"],
            "session_preference": ["asian", "london", "newyork"],
            "hold_duration": "scalp",
            "news_avoidance": False,
            "volatility_tolerance": "high",
            "drawdown_sensitivity": "low"
        }
    }
    
    base = personalities.get(risk_level, personalities["moderate"])
    
    return {
        **base,
        "personality_id": str(uuid4()),
        "variance_factor": random.uniform(0.8, 1.2),  # ±20% variance
        "timing_offset": random.randint(-300, 300),   # ±5 minutes
        "lot_size_variance": random.uniform(0.9, 1.1), # ±10% lot variance
        "sl_tp_variance": random.uniform(0.95, 1.05),  # ±5% SL/TP variance
        "entry_delay": random.randint(0, 2000),        # 0-2 second delay
        "preferred_pairs": random.sample(
            ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD"], 
            random.randint(2, 4)
        )
    }


def generate_trade_history(account_id: str, days: int = 30) -> List[Dict]:
    """Generate realistic trade history"""
    
    trades = []
    current_time = datetime.now() - timedelta(days=days)
    
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "XAUUSD"]
    
    for day in range(days):
        # Random number of trades per day (0-5)
        daily_trades = random.randint(0, 5)
        
        for _ in range(daily_trades):
            symbol = random.choice(symbols)
            action = random.choice(["BUY", "SELL"])
            lot_size = round(random.uniform(0.01, 0.5), 2)
            
            # Realistic pricing based on symbol
            if symbol == "USDJPY":
                entry = round(random.uniform(140.0, 150.0), 3)
                sl_distance = random.uniform(0.2, 0.8)
                tp_distance = random.uniform(0.3, 1.2)
            elif symbol == "XAUUSD":
                entry = round(random.uniform(1900.0, 2100.0), 2)
                sl_distance = random.uniform(5.0, 25.0)
                tp_distance = random.uniform(8.0, 40.0)
            else:  # Major pairs
                entry = round(random.uniform(0.9, 1.4), 5)
                sl_distance = random.uniform(0.0015, 0.0080)
                tp_distance = random.uniform(0.0020, 0.0120)
            
            # Calculate SL/TP based on action
            if action == "BUY":
                stop_loss = round(entry - sl_distance, 5)
                take_profit = round(entry + tp_distance, 5)
            else:
                stop_loss = round(entry + sl_distance, 5)
                take_profit = round(entry - tp_distance, 5)
            
            # Trade outcome (70% win rate for testing)
            outcome = "win" if random.random() < 0.7 else "loss"
            
            if outcome == "win":
                exit_price = take_profit
                pnl = lot_size * tp_distance * 100000  # Simplified P&L
            else:
                exit_price = stop_loss
                pnl = -lot_size * sl_distance * 100000
            
            trade = {
                "trade_id": str(uuid4()),
                "account_id": account_id,
                "symbol": symbol,
                "action": action,
                "lot_size": lot_size,
                "entry_price": entry,
                "exit_price": exit_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "entry_time": current_time.isoformat(),
                "exit_time": (current_time + timedelta(hours=random.randint(1, 12))).isoformat(),
                "pnl": round(pnl, 2),
                "commission": round(lot_size * 7.0, 2),  # $7 per lot
                "swap": round(random.uniform(-2.0, 2.0), 2),
                "outcome": outcome,
                "hold_duration_minutes": random.randint(60, 720),
                "agent_signal": random.choice(["wyckoff", "aria", "smc", "market_state"]),
                "confidence": random.uniform(0.65, 0.95)
            }
            
            trades.append(trade)
            current_time += timedelta(hours=random.randint(1, 6))
    
    return sorted(trades, key=lambda x: x["entry_time"])


def generate_account_metrics(trades: List[Dict]) -> Dict:
    """Calculate account metrics from trade history"""
    
    if not trades:
        return {}
    
    total_pnl = sum(t["pnl"] for t in trades)
    winning_trades = [t for t in trades if t["outcome"] == "win"]
    losing_trades = [t for t in trades if t["outcome"] == "loss"]
    
    avg_win = sum(t["pnl"] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = abs(sum(t["pnl"] for t in losing_trades) / len(losing_trades)) if losing_trades else 0
    
    return {
        "total_trades": len(trades),
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": len(winning_trades) / len(trades) if trades else 0,
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": avg_win / avg_loss if avg_loss > 0 else float('inf'),
        "largest_win": max((t["pnl"] for t in trades), default=0),
        "largest_loss": min((t["pnl"] for t in trades), default=0),
        "consecutive_wins": 0,  # Would need more complex calculation
        "consecutive_losses": 0,  # Would need more complex calculation
        "avg_hold_time_hours": sum(t["hold_duration_minutes"] for t in trades) / len(trades) / 60,
        "best_symbol": max(set(t["symbol"] for t in trades), key=lambda s: sum(t["pnl"] for t in trades if t["symbol"] == s)),
        "total_commission": sum(t["commission"] for t in trades),
        "total_swap": sum(t["swap"] for t in trades)
    }


# Sample account configurations for different scenarios
SAMPLE_ACCOUNTS = {
    "profitable_challenge": generate_prop_firm_account("FTMO", "challenge", 50000),
    "struggling_funded": generate_prop_firm_account("MyForexFunds", "funded", 100000),
    "new_verification": generate_prop_firm_account("FundedNext", "verification", 25000)
}

SAMPLE_PERSONALITIES = {
    "conservative_london": generate_trading_personality("conservative"),
    "aggressive_scalper": generate_trading_personality("aggressive"),
    "balanced_swing": generate_trading_personality("moderate")
}