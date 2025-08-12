use chrono::{Duration, Utc};
use execution_engine::risk::{
    DrawdownAlertManager, DrawdownTracker, EquityHistoryManager, EquityPoint,
};
use rust_decimal_macros::dec;
use std::sync::Arc;
use uuid::Uuid;

#[tokio::test]
async fn test_maximum_drawdown_calculation() {
    let equity_history_manager = Arc::new(EquityHistoryManager::new());
    let drawdown_alert_manager = Arc::new(DrawdownAlertManager::new());
    let tracker = DrawdownTracker::new(equity_history_manager.clone(), drawdown_alert_manager);

    let account_id = Uuid::new_v4();

    let equity_points = vec![
        (dec!(10000), Utc::now() - Duration::days(10)),
        (dec!(11000), Utc::now() - Duration::days(9)),
        (dec!(12000), Utc::now() - Duration::days(8)),
        (dec!(10500), Utc::now() - Duration::days(7)),
        (dec!(9500), Utc::now() - Duration::days(6)),
        (dec!(10000), Utc::now() - Duration::days(5)),
        (dec!(10500), Utc::now() - Duration::days(4)),
        (dec!(11000), Utc::now() - Duration::days(3)),
        (dec!(10800), Utc::now() - Duration::days(2)),
        (dec!(11200), Utc::now() - Duration::days(1)),
        (dec!(11500), Utc::now()),
    ];

    for (equity, timestamp) in equity_points {
        equity_history_manager
            .record_equity(account_id, equity, equity)
            .await
            .unwrap();
    }

    let metrics = tracker.calculate_drawdowns(account_id).await.unwrap();

    assert!(metrics.maximum_drawdown.amount > dec!(0));
    assert_eq!(metrics.maximum_drawdown.amount, dec!(2500));
    assert!(metrics.maximum_drawdown.percentage > dec!(20));
}

#[tokio::test]
async fn test_daily_drawdown_calculation() {
    let equity_history_manager = Arc::new(EquityHistoryManager::new());
    let drawdown_alert_manager = Arc::new(DrawdownAlertManager::new());
    let tracker = DrawdownTracker::new(equity_history_manager.clone(), drawdown_alert_manager);

    let account_id = Uuid::new_v4();

    let today = Utc::now();
    let equity_points = vec![
        (dec!(10000), today - Duration::hours(8)),
        (dec!(10200), today - Duration::hours(6)),
        (dec!(10500), today - Duration::hours(4)),
        (dec!(10300), today - Duration::hours(2)),
        (dec!(10100), today),
    ];

    for (equity, timestamp) in &equity_points {
        let point = EquityPoint {
            equity: *equity,
            balance: *equity,
            timestamp: *timestamp,
        };
        equity_history_manager
            .history
            .entry(account_id)
            .or_insert_with(Vec::new)
            .push(point);
    }

    let metrics = tracker.calculate_drawdowns(account_id).await.unwrap();

    assert_eq!(metrics.daily_drawdown.peak_equity, dec!(10500));
    assert_eq!(metrics.daily_drawdown.current_equity, dec!(10100));
    assert_eq!(metrics.daily_drawdown.amount, dec!(400));
}

#[tokio::test]
async fn test_weekly_drawdown_calculation() {
    let equity_history_manager = Arc::new(EquityHistoryManager::new());
    let drawdown_alert_manager = Arc::new(DrawdownAlertManager::new());
    let tracker = DrawdownTracker::new(equity_history_manager.clone(), drawdown_alert_manager);

    let account_id = Uuid::new_v4();

    let equity_points = vec![
        (dec!(10000), Utc::now() - Duration::days(6)),
        (dec!(10500), Utc::now() - Duration::days(5)),
        (dec!(11000), Utc::now() - Duration::days(4)),
        (dec!(10800), Utc::now() - Duration::days(3)),
        (dec!(10600), Utc::now() - Duration::days(2)),
        (dec!(10400), Utc::now() - Duration::days(1)),
        (dec!(10200), Utc::now()),
    ];

    for (equity, timestamp) in equity_points {
        equity_history_manager
            .record_equity(account_id, equity, equity)
            .await
            .unwrap();
    }

    let metrics = tracker.calculate_drawdowns(account_id).await.unwrap();

    assert_eq!(metrics.weekly_drawdown.peak_equity, dec!(11000));
    assert_eq!(metrics.weekly_drawdown.current_equity, dec!(10200));
    assert_eq!(metrics.weekly_drawdown.amount, dec!(800));
}

#[tokio::test]
async fn test_recovery_factor_calculation() {
    let equity_history_manager = Arc::new(EquityHistoryManager::new());
    let drawdown_alert_manager = Arc::new(DrawdownAlertManager::new());
    let tracker = DrawdownTracker::new(equity_history_manager.clone(), drawdown_alert_manager);

    let account_id = Uuid::new_v4();

    let equity_points = vec![
        (dec!(10000), Utc::now() - Duration::days(5)),
        (dec!(12000), Utc::now() - Duration::days(4)),
        (dec!(9000), Utc::now() - Duration::days(3)),
        (dec!(11000), Utc::now() - Duration::days(2)),
        (dec!(13000), Utc::now() - Duration::days(1)),
        (dec!(13000), Utc::now()),
    ];

    for (equity, timestamp) in equity_points {
        equity_history_manager
            .record_equity(account_id, equity, equity)
            .await
            .unwrap();
    }

    let metrics = tracker.calculate_drawdowns(account_id).await.unwrap();

    assert_eq!(metrics.recovery_factor, dec!(1));
}

#[tokio::test]
async fn test_drawdown_based_position_sizing() {
    let equity_history_manager = Arc::new(EquityHistoryManager::new());
    let drawdown_alert_manager = Arc::new(DrawdownAlertManager::new());
    let tracker = DrawdownTracker::new(equity_history_manager.clone(), drawdown_alert_manager);

    let account_id = Uuid::new_v4();

    let equity_points = vec![
        (dec!(10000), Utc::now() - Duration::days(3)),
        (dec!(12000), Utc::now() - Duration::days(2)),
        (dec!(9000), Utc::now() - Duration::days(1)),
        (dec!(9500), Utc::now()),
    ];

    for (equity, timestamp) in equity_points {
        equity_history_manager
            .record_equity(account_id, equity, equity)
            .await
            .unwrap();
    }

    let _ = tracker.calculate_drawdowns(account_id).await.unwrap();

    let adjusted_risk = tracker
        .trigger_drawdown_based_position_sizing(account_id)
        .await
        .unwrap();

    assert!(adjusted_risk < dec!(2));
    assert_eq!(adjusted_risk, dec!(1));
}
