#!/usr/bin/env python3
"""
Cycle-Session Integration System
================================
Integrates trading session analysis with our optimized cycle configurations.

Features:
- Run session analysis for all 4 cycles (Cycle 2, 3, 4, 5)
- Compare session performance across different parameter sets
- Generate session-optimized recommendations for each cycle
- Identify best cycle-session combinations
"""

import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List
import logging

# Import our existing components
from trading_session_analyzer import SessionAnalyzer, TradingSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CycleSessionIntegration:
    """Integration system for cycle configurations with session analysis"""

    def __init__(self):
        """Initialize integration system"""
        self.session_analyzer = SessionAnalyzer()

        # Define our 4 optimized cycle configurations
        self.cycle_configs = {
            'Cycle_2_Ultra_Selective': {
                'name': 'Ultra_Selective',
                'confidence_threshold': 85.0,
                'min_volume_confirmation': 80.0,
                'min_structure_score': 75.0,
                'min_risk_reward': 4.0,
                'atr_multiplier_stop': 0.3,
                'enable_regime_filter': True,
                'enable_frequency_management': True,
                'expected_signals_per_month': 8,
                'expected_win_rate': 75.0
            },
            'Cycle_3_Multi_Timeframe': {
                'name': 'Multi_Timeframe_Precision',
                'confidence_threshold': 78.0,
                'min_volume_confirmation': 70.0,
                'min_structure_score': 68.0,
                'min_risk_reward': 3.5,
                'atr_multiplier_stop': 0.4,
                'enable_regime_filter': True,
                'enable_frequency_management': True,
                'expected_signals_per_month': 12,
                'expected_win_rate': 46.0
            },
            'Cycle_4_Balanced_Aggressive': {
                'name': 'Balanced_Aggressive',
                'confidence_threshold': 70.0,
                'min_volume_confirmation': 60.0,
                'min_structure_score': 58.0,
                'min_risk_reward': 2.8,
                'atr_multiplier_stop': 0.6,
                'enable_regime_filter': False,
                'enable_frequency_management': True,
                'expected_signals_per_month': 25,
                'expected_win_rate': 50.0
            },
            'Cycle_5_Dynamic_Adaptive': {
                'name': 'Dynamic_Adaptive',
                'confidence_threshold': 72.0,
                'min_volume_confirmation': 65.0,
                'min_structure_score': 62.0,
                'min_risk_reward': 3.2,
                'atr_multiplier_stop': 0.45,
                'enable_regime_filter': True,
                'enable_frequency_management': True,
                'expected_signals_per_month': 18,
                'expected_win_rate': 61.0
            }
        }

    def run_comprehensive_cycle_session_analysis(self,
                                                months_to_test: int = 6,
                                                currency_pairs: List[str] = ["EUR_USD", "GBP_USD", "USD_JPY"]) -> Dict:
        """
        Run comprehensive session analysis for all cycle configurations.
        """

        print("Comprehensive Cycle-Session Analysis")
        print("=" * 60)
        print(f"Testing {len(self.cycle_configs)} cycle configurations")
        print(f"Analysis period: {months_to_test} months")
        print(f"Currency pairs: {', '.join(currency_pairs)}")
        print()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_to_test * 30)

        results = {}

        # Analyze each cycle configuration
        for cycle_name, config in self.cycle_configs.items():
            print(f"Analyzing {cycle_name}...")

            # Run session-aware backtest for this cycle
            trades = self.session_analyzer.run_session_aware_backtest(
                config=config,
                start_date=start_date,
                end_date=end_date,
                currency_pairs=currency_pairs
            )

            # Analyze session performance
            session_results = self.session_analyzer.analyze_session_performance(trades)

            # Generate session report
            session_report = self.session_analyzer.generate_session_report(session_results)

            results[cycle_name] = {
                'config': config,
                'total_trades': len(trades),
                'session_results': session_results,
                'session_report': session_report,
                'trades': trades
            }

            print(f"  {cycle_name}: {len(trades)} trades generated")

        return results

    def compare_cycle_session_performance(self, results: Dict) -> Dict:
        """
        Compare session performance across all cycle configurations.
        """

        comparison = {
            'cycle_session_matrix': {},
            'best_cycle_per_session': {},
            'session_rankings_by_cycle': {},
            'optimal_combinations': [],
            'summary_statistics': {}
        }

        # Create performance matrix: [Cycle][Session] = Performance
        sessions_to_analyze = [
            TradingSession.LONDON,
            TradingSession.NEW_YORK,
            TradingSession.TOKYO,
            TradingSession.SYDNEY,
            TradingSession.LONDON_NY_OVERLAP
        ]

        cycle_session_matrix = {}

        for cycle_name, result in results.items():
            cycle_session_matrix[cycle_name] = {}

            for session in sessions_to_analyze:
                if session in result['session_results']:
                    perf = result['session_results'][session]
                    cycle_session_matrix[cycle_name][session.value] = {
                        'total_pnl': perf.total_pnl_dollars,
                        'win_rate': perf.win_rate,
                        'total_trades': perf.total_trades,
                        'profit_factor': perf.profit_factor,
                        'avg_risk_reward': perf.avg_risk_reward,
                        'sharpe_ratio': perf.sharpe_ratio
                    }
                else:
                    cycle_session_matrix[cycle_name][session.value] = {
                        'total_pnl': 0,
                        'win_rate': 0,
                        'total_trades': 0,
                        'profit_factor': 0,
                        'avg_risk_reward': 0,
                        'sharpe_ratio': 0
                    }

        comparison['cycle_session_matrix'] = cycle_session_matrix

        # Find best cycle for each session
        for session in sessions_to_analyze:
            session_performances = []

            for cycle_name, result in results.items():
                if session in result['session_results']:
                    perf = result['session_results'][session]
                    session_performances.append((cycle_name, perf.total_pnl_dollars))

            if session_performances:
                best_cycle, best_pnl = max(session_performances, key=lambda x: x[1])
                comparison['best_cycle_per_session'][session.value] = {
                    'best_cycle': best_cycle,
                    'best_pnl': best_pnl
                }

        # Find optimal combinations (profitable cycle-session pairs)
        optimal_combinations = []

        for cycle_name, result in results.items():
            for session, perf in result['session_results'].items():
                if perf.total_pnl_dollars > 0 and perf.total_trades >= 5:  # Minimum criteria
                    optimal_combinations.append({
                        'cycle': cycle_name,
                        'session': session.value,
                        'total_pnl': perf.total_pnl_dollars,
                        'win_rate': perf.win_rate,
                        'total_trades': perf.total_trades,
                        'profit_factor': perf.profit_factor,
                        'score': perf.total_pnl_dollars * (perf.win_rate / 100) * perf.profit_factor
                    })

        # Sort by composite score
        optimal_combinations.sort(key=lambda x: x['score'], reverse=True)
        comparison['optimal_combinations'] = optimal_combinations

        # Summary statistics
        total_trades_all = sum(result['total_trades'] for result in results.values())
        total_pnl_all = sum(
            sum(perf.total_pnl_dollars for perf in result['session_results'].values())
            for result in results.values()
        )

        comparison['summary_statistics'] = {
            'total_trades_analyzed': total_trades_all,
            'total_pnl_all_cycles': total_pnl_all,
            'cycles_analyzed': len(results),
            'sessions_analyzed': len(sessions_to_analyze)
        }

        return comparison

    def generate_optimization_recommendations(self, results: Dict, comparison: Dict) -> List[str]:
        """
        Generate actionable optimization recommendations based on cycle-session analysis.
        """

        recommendations = []

        # Find overall best performing combination
        if comparison['optimal_combinations']:
            best_combo = comparison['optimal_combinations'][0]
            recommendations.append(
                f"OPTIMAL STRATEGY: Deploy {best_combo['cycle']} during {best_combo['session']} "
                f"session (${best_combo['total_pnl']:,.0f} profit, {best_combo['win_rate']:.1f}% win rate)"
            )

        # Session-specific recommendations
        for session, best_info in comparison['best_cycle_per_session'].items():
            if best_info['best_pnl'] > 0:
                recommendations.append(
                    f"{session.upper()}: Use {best_info['best_cycle']} configuration "
                    f"(${best_info['best_pnl']:,.0f} profit potential)"
                )

        # Risk management recommendations
        high_risk_combinations = [
            combo for combo in comparison['optimal_combinations']
            if combo['win_rate'] < 40
        ]

        for combo in high_risk_combinations[:3]:  # Top 3 risky combinations
            recommendations.append(
                f"RISK WARNING: {combo['cycle']} + {combo['session']} shows low win rate "
                f"({combo['win_rate']:.1f}%) - increase position sizing caution"
            )

        # Volume recommendations
        high_volume_combinations = [
            combo for combo in comparison['optimal_combinations']
            if combo['total_trades'] >= 20
        ]

        if high_volume_combinations:
            best_volume = high_volume_combinations[0]
            recommendations.append(
                f"HIGH FREQUENCY: {best_volume['cycle']} + {best_volume['session']} "
                f"provides {best_volume['total_trades']} trades with ${best_volume['total_pnl']:,.0f} profit"
            )

        return recommendations

    def print_comprehensive_analysis(self, results: Dict, comparison: Dict):
        """
        Print comprehensive cycle-session analysis results.
        """

        print("\n" + "="*80)
        print("COMPREHENSIVE CYCLE-SESSION ANALYSIS RESULTS")
        print("="*80)

        # Performance Matrix
        print(f"\nPERFORMANCE MATRIX (Total P&L in USD):")
        print(f"{'CYCLE':<25} {'LONDON':<12} {'NEW_YORK':<12} {'TOKYO':<12} {'SYDNEY':<12}")
        print("-" * 80)

        for cycle_name in results.keys():
            cycle_short = cycle_name.replace('Cycle_', '').replace('_', ' ')
            matrix = comparison['cycle_session_matrix'][cycle_name]

            london_pnl = matrix.get('London', {}).get('total_pnl', 0)
            ny_pnl = matrix.get('New_York', {}).get('total_pnl', 0)
            tokyo_pnl = matrix.get('Tokyo', {}).get('total_pnl', 0)
            sydney_pnl = matrix.get('Sydney', {}).get('total_pnl', 0)

            print(f"{cycle_short:<25} {london_pnl:>+10,.0f} {ny_pnl:>+10,.0f} {tokyo_pnl:>+10,.0f} {sydney_pnl:>+10,.0f}")

        # Best combinations
        print(f"\nTOP 10 OPTIMAL CYCLE-SESSION COMBINATIONS:")
        print(f"{'RANK':<6} {'CYCLE':<20} {'SESSION':<15} {'P&L':<12} {'WIN RATE':<10} {'TRADES':<8}")
        print("-" * 80)

        for i, combo in enumerate(comparison['optimal_combinations'][:10], 1):
            cycle_short = combo['cycle'].replace('Cycle_', '').replace('_', ' ')
            print(f"{i:<6} {cycle_short:<20} {combo['session']:<15} "
                  f"${combo['total_pnl']:>9,.0f} {combo['win_rate']:>7.1f}% {combo['total_trades']:>6}")

        # Session winners
        print(f"\nBEST CYCLE FOR EACH SESSION:")
        print("-" * 40)
        for session, info in comparison['best_cycle_per_session'].items():
            cycle_short = info['best_cycle'].replace('Cycle_', '').replace('_', ' ')
            print(f"{session:<15}: {cycle_short} (${info['best_pnl']:+,.0f})")

        # Summary statistics
        stats = comparison['summary_statistics']
        print(f"\nSUMMARY STATISTICS:")
        print(f"  Total Trades Analyzed: {stats['total_trades_analyzed']}")
        print(f"  Total P&L All Cycles: ${stats['total_pnl_all_cycles']:+,.2f}")
        print(f"  Cycles Analyzed: {stats['cycles_analyzed']}")
        print(f"  Sessions Analyzed: {stats['sessions_analyzed']}")

def main():
    """Main execution function"""

    print("Cycle-Session Integration Analysis")
    print("=" * 50)
    print("Analyzing all optimized cycles across trading sessions")
    print()

    # Initialize integration system
    integration = CycleSessionIntegration()

    # Run comprehensive analysis
    results = integration.run_comprehensive_cycle_session_analysis(
        months_to_test=3,  # 3-month analysis
        currency_pairs=["EUR_USD", "GBP_USD", "USD_JPY"]
    )

    # Compare performance across cycles and sessions
    comparison = integration.compare_cycle_session_performance(results)

    # Print comprehensive analysis
    integration.print_comprehensive_analysis(results, comparison)

    # Generate recommendations
    recommendations = integration.generate_optimization_recommendations(results, comparison)

    print(f"\nOPTIMIZATION RECOMMENDATIONS:")
    print("-" * 40)
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Prepare data for JSON serialization
    json_results = {}
    for cycle_name, result in results.items():
        json_results[cycle_name] = {
            'config': result['config'],
            'total_trades': result['total_trades'],
            'session_report': result['session_report']
        }

    comprehensive_report = {
        'cycle_results': json_results,
        'comparison_analysis': comparison,
        'recommendations': recommendations,
        'analysis_timestamp': timestamp
    }

    report_file = f"comprehensive_cycle_session_analysis_{timestamp}.json"
    with open(report_file, 'w') as f:
        json.dump(comprehensive_report, f, indent=2, default=str)

    print(f"\nComprehensive report saved: {report_file}")

    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)