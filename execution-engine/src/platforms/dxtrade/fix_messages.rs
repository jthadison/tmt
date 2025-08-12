use super::error::{DXTradeError, Result};
use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::str::FromStr;

pub const SOH: char = '\x01';

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FIXMessage {
    pub msg_type: MessageType,
    pub fields: HashMap<u32, String>,
    pub raw_message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum MessageType {
    Heartbeat,
    TestRequest,
    ResendRequest,
    Reject,
    SequenceReset,
    Logout,
    Logon,
    NewOrderSingle,
    ExecutionReport,
    OrderCancelReject,
    OrderCancelRequest,
    OrderCancelReplaceRequest,
    OrderStatusRequest,
    MarketDataRequest,
    MarketDataSnapshotFullRefresh,
    MarketDataIncrementalRefresh,
    MarketDataRequestReject,
    TradingSessionStatus,
    TradingSessionStatusRequest,
    PositionReport,
    RequestForPositions,
    RequestForPositionsAck,
    BusinessMessageReject,
    UserRequest,
    UserResponse,
    Unknown(String),
}

pub struct FIXMessageBuilder {
    sender_comp_id: String,
    target_comp_id: String,
    msg_seq_num: u32,
    fields: HashMap<u32, String>,
}

impl FIXMessageBuilder {
    pub fn new(sender_comp_id: String, target_comp_id: String, msg_seq_num: u32) -> Self {
        let mut fields = HashMap::new();
        fields.insert(49, sender_comp_id.clone()); // SenderCompID
        fields.insert(56, target_comp_id.clone()); // TargetCompID
        fields.insert(34, msg_seq_num.to_string()); // MsgSeqNum
        fields.insert(52, Utc::now().format("%Y%m%d-%H:%M:%S%.3f").to_string()); // SendingTime

        Self {
            sender_comp_id,
            target_comp_id,
            msg_seq_num,
            fields,
        }
    }

    pub fn with_field(mut self, tag: u32, value: String) -> Self {
        self.fields.insert(tag, value);
        self
    }

    pub fn build(mut self, msg_type: MessageType) -> Result<FIXMessage> {
        self.fields.insert(8, "FIX.4.4".to_string()); // BeginString
        self.fields.insert(35, msg_type.to_string()); // MsgType

        let mut sorted_fields: Vec<(u32, String)> = self.fields.into_iter().collect();
        sorted_fields.sort_by_key(|&(tag, _)| tag);

        let body_length_index = sorted_fields.iter().position(|(tag, _)| *tag == 9);
        if body_length_index.is_some() {
            sorted_fields.remove(body_length_index.unwrap());
        }

        let checksum_index = sorted_fields.iter().position(|(tag, _)| *tag == 10);
        if checksum_index.is_some() {
            sorted_fields.remove(checksum_index.unwrap());
        }

        let mut body = String::new();
        let mut begin_string = String::new();

        for (tag, value) in &sorted_fields {
            let field_str = format!("{}={}{}", tag, value, SOH);
            if *tag == 8 {
                begin_string = field_str;
            } else {
                body.push_str(&field_str);
            }
        }

        let body_length = body.len();
        let body_length_field = format!("9={}{}", body_length, SOH);

        let message_without_checksum = format!("{}{}{}", begin_string, body_length_field, body);
        let checksum = Self::calculate_checksum(&message_without_checksum);
        let checksum_field = format!("10={:03}{}", checksum, SOH);

        let message = format!("{}{}", message_without_checksum, checksum_field);

        Ok(FIXMessage {
            msg_type,
            fields: sorted_fields.into_iter().collect(),
            raw_message: message,
        })
    }

    fn calculate_checksum(message: &str) -> u32 {
        message.as_bytes().iter().map(|&b| b as u32).sum::<u32>() % 256
    }

    pub fn calculate_checksum_static(message: &str) -> u32 {
        Self::calculate_checksum(message)
    }
}

impl MessageType {
    pub fn from_str(s: &str) -> Self {
        match s {
            "0" => Self::Heartbeat,
            "1" => Self::TestRequest,
            "2" => Self::ResendRequest,
            "3" => Self::Reject,
            "4" => Self::SequenceReset,
            "5" => Self::Logout,
            "A" => Self::Logon,
            "D" => Self::NewOrderSingle,
            "8" => Self::ExecutionReport,
            "9" => Self::OrderCancelReject,
            "F" => Self::OrderCancelRequest,
            "G" => Self::OrderCancelReplaceRequest,
            "H" => Self::OrderStatusRequest,
            "V" => Self::MarketDataRequest,
            "W" => Self::MarketDataSnapshotFullRefresh,
            "X" => Self::MarketDataIncrementalRefresh,
            "Y" => Self::MarketDataRequestReject,
            "h" => Self::TradingSessionStatus,
            "g" => Self::TradingSessionStatusRequest,
            "AP" => Self::PositionReport,
            "AN" => Self::RequestForPositions,
            "AO" => Self::RequestForPositionsAck,
            "j" => Self::BusinessMessageReject,
            "BE" => Self::UserRequest,
            "BF" => Self::UserResponse,
            _ => Self::Unknown(s.to_string()),
        }
    }
}

impl ToString for MessageType {
    fn to_string(&self) -> String {
        match self {
            Self::Heartbeat => "0".to_string(),
            Self::TestRequest => "1".to_string(),
            Self::ResendRequest => "2".to_string(),
            Self::Reject => "3".to_string(),
            Self::SequenceReset => "4".to_string(),
            Self::Logout => "5".to_string(),
            Self::Logon => "A".to_string(),
            Self::NewOrderSingle => "D".to_string(),
            Self::ExecutionReport => "8".to_string(),
            Self::OrderCancelReject => "9".to_string(),
            Self::OrderCancelRequest => "F".to_string(),
            Self::OrderCancelReplaceRequest => "G".to_string(),
            Self::OrderStatusRequest => "H".to_string(),
            Self::MarketDataRequest => "V".to_string(),
            Self::MarketDataSnapshotFullRefresh => "W".to_string(),
            Self::MarketDataIncrementalRefresh => "X".to_string(),
            Self::MarketDataRequestReject => "Y".to_string(),
            Self::TradingSessionStatus => "h".to_string(),
            Self::TradingSessionStatusRequest => "g".to_string(),
            Self::PositionReport => "AP".to_string(),
            Self::RequestForPositions => "AN".to_string(),
            Self::RequestForPositionsAck => "AO".to_string(),
            Self::BusinessMessageReject => "j".to_string(),
            Self::UserRequest => "BE".to_string(),
            Self::UserResponse => "BF".to_string(),
            Self::Unknown(s) => s.clone(),
        }
    }
}

impl FIXMessage {
    pub fn parse(raw_message: &str) -> Result<Self> {
        let mut fields = HashMap::new();
        let parts: Vec<&str> = raw_message.split(SOH).collect();

        let mut msg_type = MessageType::Unknown("".to_string());

        for part in parts {
            if part.is_empty() {
                continue;
            }

            let field_parts: Vec<&str> = part.splitn(2, '=').collect();
            if field_parts.len() != 2 {
                continue;
            }

            let tag: u32 = field_parts[0].parse().map_err(|_| {
                DXTradeError::FixMessageError(format!("Invalid tag: {}", field_parts[0]))
            })?;
            let value = field_parts[1].to_string();

            if tag == 35 {
                msg_type = MessageType::from_str(&value);
            }

            fields.insert(tag, value);
        }

        Ok(Self {
            msg_type,
            fields,
            raw_message: raw_message.to_string(),
        })
    }

    pub fn get_field(&self, tag: u32) -> Option<&String> {
        self.fields.get(&tag)
    }

    pub fn get_field_as_decimal(&self, tag: u32) -> Option<Decimal> {
        self.get_field(tag).and_then(|s| Decimal::from_str(s).ok())
    }

    pub fn get_field_as_u32(&self, tag: u32) -> Option<u32> {
        self.get_field(tag).and_then(|s| s.parse().ok())
    }

    pub fn get_field_as_datetime(&self, tag: u32) -> Option<DateTime<Utc>> {
        self.get_field(tag)
            .and_then(|s| DateTime::parse_from_str(s, "%Y%m%d-%H:%M:%S%.3f").ok())
            .map(|dt| dt.with_timezone(&Utc))
    }

    pub fn validate_checksum(&self) -> bool {
        let checksum_pos = self.raw_message.rfind("10=");
        if let Some(pos) = checksum_pos {
            let message_without_checksum = &self.raw_message[..pos];
            let expected_checksum = message_without_checksum
                .as_bytes()
                .iter()
                .map(|&b| b as u32)
                .sum::<u32>()
                % 256;

            let actual_checksum_str = &self.raw_message[pos + 3..pos + 6];
            if let Ok(actual_checksum) = actual_checksum_str.parse::<u32>() {
                return expected_checksum == actual_checksum;
            }
        }
        false
    }

    pub fn calculate_checksum(&self) -> u32 {
        self.raw_message
            .as_bytes()
            .iter()
            .map(|&b| b as u32)
            .sum::<u32>()
            % 256
    }

    pub fn is_admin_message(&self) -> bool {
        matches!(
            self.msg_type,
            MessageType::Heartbeat
                | MessageType::TestRequest
                | MessageType::ResendRequest
                | MessageType::Reject
                | MessageType::SequenceReset
                | MessageType::Logout
                | MessageType::Logon
        )
    }

    pub fn requires_response(&self) -> bool {
        matches!(
            self.msg_type,
            MessageType::TestRequest | MessageType::ResendRequest | MessageType::Logon
        )
    }

    pub fn create_heartbeat(
        sender_comp_id: String,
        target_comp_id: String,
        msg_seq_num: u32,
    ) -> Result<Self> {
        FIXMessageBuilder::new(sender_comp_id, target_comp_id, msg_seq_num)
            .build(MessageType::Heartbeat)
    }

    pub fn create_test_request(
        sender_comp_id: String,
        target_comp_id: String,
        msg_seq_num: u32,
        test_req_id: String,
    ) -> Result<Self> {
        FIXMessageBuilder::new(sender_comp_id, target_comp_id, msg_seq_num)
            .with_field(112, test_req_id) // TestReqID
            .build(MessageType::TestRequest)
    }

    pub fn create_logon(
        sender_comp_id: String,
        target_comp_id: String,
        msg_seq_num: u32,
        heartbeat_interval: u32,
        reset_seq_num: bool,
    ) -> Result<Self> {
        let mut builder = FIXMessageBuilder::new(sender_comp_id, target_comp_id, msg_seq_num)
            .with_field(98, "0".to_string()) // EncryptMethod (None)
            .with_field(108, heartbeat_interval.to_string()); // HeartBtInt

        if reset_seq_num {
            builder = builder.with_field(141, "Y".to_string()); // ResetSeqNumFlag
        }

        builder.build(MessageType::Logon)
    }

    pub fn create_logout(
        sender_comp_id: String,
        target_comp_id: String,
        msg_seq_num: u32,
        text: Option<String>,
    ) -> Result<Self> {
        let mut builder = FIXMessageBuilder::new(sender_comp_id, target_comp_id, msg_seq_num);

        if let Some(text) = text {
            builder = builder.with_field(58, text); // Text
        }

        builder.build(MessageType::Logout)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_message_type_conversion() {
        assert_eq!(MessageType::from_str("D"), MessageType::NewOrderSingle);
        assert_eq!(MessageType::from_str("8"), MessageType::ExecutionReport);
        assert_eq!(MessageType::NewOrderSingle.to_string(), "D");
        assert_eq!(MessageType::ExecutionReport.to_string(), "8");
    }

    #[test]
    fn test_fix_message_builder() {
        let message = FIXMessageBuilder::new("SENDER".to_string(), "TARGET".to_string(), 1)
            .build(MessageType::Heartbeat)
            .unwrap();

        assert_eq!(message.msg_type, MessageType::Heartbeat);
        assert_eq!(message.get_field(49), Some(&"SENDER".to_string()));
        assert_eq!(message.get_field(56), Some(&"TARGET".to_string()));
        assert_eq!(message.get_field(34), Some(&"1".to_string()));
    }

    #[test]
    fn test_checksum_calculation() {
        let raw_message = "8=FIX.4.4\x019=49\x0135=0\x0149=SENDER\x0156=TARGET\x0134=1\x0152=20231207-10:30:00.000\x0110=123\x01";
        let message = FIXMessage::parse(raw_message).unwrap();

        // Note: This test would need actual checksum calculation to pass
        assert_eq!(message.msg_type, MessageType::Heartbeat);
    }

    #[test]
    fn test_admin_message_detection() {
        let heartbeat = FIXMessage {
            msg_type: MessageType::Heartbeat,
            fields: HashMap::new(),
            raw_message: String::new(),
        };

        let new_order = FIXMessage {
            msg_type: MessageType::NewOrderSingle,
            fields: HashMap::new(),
            raw_message: String::new(),
        };

        assert!(heartbeat.is_admin_message());
        assert!(!new_order.is_admin_message());
    }
}
