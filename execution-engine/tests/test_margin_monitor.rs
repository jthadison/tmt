use chrono::Utc;
use execution_engine::risk::{
    Account, AccountManager, MarginAlertManager, MarginCalculator, MarginMonitor,
    MarginProtectionSystem, Position, PositionType, ProposedPosition,
};
use rust_decimal_macros::dec;
use std::sync::Arc;
use uuid::Uuid;

#[tokio::test]
async fn test_margin_level_calculation() {
    let account_manager = Arc::new(AccountManager::new());
    let margin_calculator = Arc::new(MarginCalculator::new());
    let margin_alerts = Arc::new(MarginAlertManager::new());
    let margin_protection = Arc::new(MarginProtectionSystem);

    let monitor = MarginMonitor::new(
        account_manager.clone(),
        margin_calculator,
        margin_alerts,
        margin_protection,
    );

    let account_id = Uuid::new_v4();
    let account = Account {
        id: account_id,
        balance: dec!(10000),
        active: true,
    };

    account_manager.add_account(account.clone()).await;

    let position = Position {
        id: Uuid::new_v4(),
        account_id,
        symbol: "EURUSD".to_string(),
        position_type: PositionType::Long,
        size: dec!(100000),
        entry_price: dec!(1.1000),
        current_price: Some(dec!(1.1050)),
        unrealized_pnl: Some(dec!(500)),
        max_favorable_excursion: dec!(500),
        max_adverse_excursion: dec!(0),
        stop_loss: Some(dec!(1.0950)),
        take_profit: Some(dec!(1.1100)),
        opened_at: Utc::now(),
    };

    account_manager.add_position(position).await;

    let margin_info = monitor.calculate_account_margin(&account).await.unwrap();

    assert_eq!(margin_info.balance, dec!(10000));
    assert_eq!(margin_info.equity, dec!(10500));
    assert_eq!(margin_info.used_margin, dec!(1100));
    assert_eq!(margin_info.free_margin, dec!(9400));
    assert!(margin_info.margin_level > dec!(900));
}

#[tokio::test]
async fn test_margin_thresholds() {
    let account_manager = Arc::new(AccountManager::new());
    let margin_calculator = Arc::new(MarginCalculator::new());
    let margin_alerts = Arc::new(MarginAlertManager::new());
    let margin_protection = Arc::new(MarginProtectionSystem);

    let monitor = MarginMonitor::new(
        account_manager.clone(),
        margin_calculator,
        margin_alerts.clone(),
        margin_protection,
    );

    let account_id = Uuid::new_v4();
    let account = Account {
        id: account_id,
        balance: dec!(10000),
        active: true,
    };

    account_manager.add_account(account.clone()).await;

    let position = Position {
        id: Uuid::new_v4(),
        account_id,
        symbol: "EURUSD".to_string(),
        position_type: PositionType::Long,
        size: dec!(800000),
        entry_price: dec!(1.1000),
        current_price: Some(dec!(1.0900)),
        unrealized_pnl: Some(dec!(-8000)),
        max_favorable_excursion: dec!(0),
        max_adverse_excursion: dec!(-8000),
        stop_loss: None,
        take_profit: None,
        opened_at: Utc::now(),
    };

    account_manager.add_position(position).await;

    let margin_info = monitor.calculate_account_margin(&account).await.unwrap();

    assert!(margin_info.margin_level < dec!(150));

    monitor
        .check_margin_thresholds(&account, &margin_info)
        .await
        .unwrap();

    assert!(margin_alerts.alerts.get(&account_id).is_some());
}

#[tokio::test]
async fn test_margin_requirements() {
    let account_manager = Arc::new(AccountManager::new());
    let margin_calculator = Arc::new(MarginCalculator::new());
    let margin_alerts = Arc::new(MarginAlertManager::new());
    let margin_protection = Arc::new(MarginProtectionSystem);

    let monitor = MarginMonitor::new(
        account_manager.clone(),
        margin_calculator,
        margin_alerts,
        margin_protection,
    );

    let account_id = Uuid::new_v4();
    let account = Account {
        id: account_id,
        balance: dec!(10000),
        active: true,
    };

    account_manager.add_account(account.clone()).await;

    let margin_info = monitor.calculate_account_margin(&account).await.unwrap();
    monitor
        .update_margin_cache(&account_id, &margin_info)
        .await
        .unwrap();

    let requirements = monitor.get_margin_requirements(account_id).await.unwrap();

    assert_eq!(requirements.account_id, account_id);
    assert!(requirements.available_for_new_positions > dec!(0));
    assert!(requirements.max_position_size_at_100_1 > dec!(0));
    assert!(requirements.max_position_size_at_50_1 > dec!(0));
}

#[tokio::test]
async fn test_margin_impact_simulation() {
    let account_manager = Arc::new(AccountManager::new());
    let margin_calculator = Arc::new(MarginCalculator::new());
    let margin_alerts = Arc::new(MarginAlertManager::new());
    let margin_protection = Arc::new(MarginProtectionSystem);

    let monitor = MarginMonitor::new(
        account_manager.clone(),
        margin_calculator,
        margin_alerts,
        margin_protection,
    );

    let account_id = Uuid::new_v4();
    let account = Account {
        id: account_id,
        balance: dec!(10000),
        active: true,
    };

    account_manager.add_account(account.clone()).await;

    let existing_position = Position {
        id: Uuid::new_v4(),
        account_id,
        symbol: "EURUSD".to_string(),
        position_type: PositionType::Long,
        size: dec!(50000),
        entry_price: dec!(1.1000),
        current_price: Some(dec!(1.1000)),
        unrealized_pnl: Some(dec!(0)),
        max_favorable_excursion: dec!(0),
        max_adverse_excursion: dec!(0),
        stop_loss: None,
        take_profit: None,
        opened_at: Utc::now(),
    };

    account_manager.add_position(existing_position).await;

    let margin_info = monitor.calculate_account_margin(&account).await.unwrap();
    monitor
        .update_margin_cache(&account_id, &margin_info)
        .await
        .unwrap();

    let proposed_position = ProposedPosition {
        symbol: "GBPUSD".to_string(),
        size: dec!(100000),
        expected_entry_price: dec!(1.3000),
    };

    let impact = monitor
        .simulate_margin_impact(account_id, &proposed_position)
        .await
        .unwrap();

    assert!(impact.current_margin_level > impact.projected_margin_level);
    assert!(impact.additional_margin_required > dec!(0));
    assert!(impact.impact_acceptable);
    assert!(impact.warning_message.is_none());
}

#[tokio::test]
async fn test_margin_impact_rejection() {
    let account_manager = Arc::new(AccountManager::new());
    let margin_calculator = Arc::new(MarginCalculator::new());
    let margin_alerts = Arc::new(MarginAlertManager::new());
    let margin_protection = Arc::new(MarginProtectionSystem);

    let monitor = MarginMonitor::new(
        account_manager.clone(),
        margin_calculator,
        margin_alerts,
        margin_protection,
    );

    let account_id = Uuid::new_v4();
    let account = Account {
        id: account_id,
        balance: dec!(10000),
        active: true,
    };

    account_manager.add_account(account.clone()).await;

    let existing_position = Position {
        id: Uuid::new_v4(),
        account_id,
        symbol: "EURUSD".to_string(),
        position_type: PositionType::Long,
        size: dec!(700000),
        entry_price: dec!(1.1000),
        current_price: Some(dec!(1.0950)),
        unrealized_pnl: Some(dec!(-3500)),
        max_favorable_excursion: dec!(0),
        max_adverse_excursion: dec!(-3500),
        stop_loss: None,
        take_profit: None,
        opened_at: Utc::now(),
    };

    account_manager.add_position(existing_position).await;

    let margin_info = monitor.calculate_account_margin(&account).await.unwrap();
    monitor
        .update_margin_cache(&account_id, &margin_info)
        .await
        .unwrap();

    let proposed_position = ProposedPosition {
        symbol: "GBPUSD".to_string(),
        size: dec!(200000),
        expected_entry_price: dec!(1.3000),
    };

    let impact = monitor
        .simulate_margin_impact(account_id, &proposed_position)
        .await
        .unwrap();

    assert!(!impact.impact_acceptable);
    assert!(impact.warning_message.is_some());
    assert!(impact.projected_margin_level < dec!(150));
}
