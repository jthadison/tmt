"""
Emergency Contact Procedures Integration
Comprehensive notification system for emergency rollback events
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.utils import formataddr
from email import encoders

logger = logging.getLogger(__name__)

class ContactType(Enum):
    """Types of emergency contacts"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TECHNICAL = "technical"
    MANAGEMENT = "management"
    EXTERNAL = "external"

class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class NotificationChannel(Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    TEAMS = "teams"
    PHONE = "phone"
    WEBHOOK = "webhook"

@dataclass
class EmergencyContact:
    """Emergency contact information"""
    id: str
    name: str
    role: str
    contact_type: ContactType
    email: Optional[str] = None
    phone: Optional[str] = None
    slack_user_id: Optional[str] = None
    teams_user_id: Optional[str] = None
    timezone: str = "UTC"
    preferred_channels: List[NotificationChannel] = None
    escalation_delay_minutes: int = 15
    active: bool = True

@dataclass
class NotificationTemplate:
    """Notification message template"""
    name: str
    priority: NotificationPriority
    channels: List[NotificationChannel]
    subject_template: str
    body_template: str
    include_attachments: bool = False

@dataclass
class NotificationResult:
    """Result of notification attempt"""
    contact_id: str
    channel: NotificationChannel
    success: bool
    timestamp: datetime
    error_message: Optional[str] = None
    delivery_id: Optional[str] = None

class EmergencyContactSystem:
    """
    Comprehensive emergency contact and notification system

    Features:
    - Multi-channel notifications (email, SMS, Slack, Teams)
    - Contact hierarchy and escalation
    - Template-based messaging
    - Delivery tracking and confirmation
    - Escalation procedures
    """

    def __init__(self):
        self.contacts: Dict[str, EmergencyContact] = {}
        self.templates: Dict[str, NotificationTemplate] = {}
        self.notification_history: List[Dict[str, Any]] = []

        # Initialize default contacts
        self._initialize_default_contacts()

        # Initialize notification templates
        self._initialize_templates()

        # Email configuration (should be set via environment variables)
        self.email_config = {
            "smtp_server": "smtp.gmail.com",  # Example SMTP server
            "smtp_port": 587,
            "username": "alerts@trading-system.com",  # Replace with actual
            "password": "app-password",  # Replace with actual app password
            "use_tls": True
        }

    def _initialize_default_contacts(self):
        """Initialize default emergency contacts"""
        default_contacts = [
            EmergencyContact(
                id="admin-001",
                name="System Administrator",
                role="Lead DevOps Engineer",
                contact_type=ContactType.PRIMARY,
                email="admin@trading-system.com",
                phone="+1-555-0101",
                preferred_channels=[NotificationChannel.EMAIL, NotificationChannel.SMS],
                escalation_delay_minutes=10
            ),
            EmergencyContact(
                id="risk-001",
                name="Risk Management Lead",
                role="Chief Risk Officer",
                contact_type=ContactType.PRIMARY,
                email="risk@trading-system.com",
                phone="+1-555-0102",
                preferred_channels=[NotificationChannel.EMAIL, NotificationChannel.PHONE],
                escalation_delay_minutes=10
            ),
            EmergencyContact(
                id="tech-001",
                name="Technical Lead",
                role="Senior Software Engineer",
                contact_type=ContactType.TECHNICAL,
                email="tech-lead@trading-system.com",
                phone="+1-555-0103",
                preferred_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
                escalation_delay_minutes=15
            ),
            EmergencyContact(
                id="mgmt-001",
                name="Trading Operations Manager",
                role="Operations Manager",
                contact_type=ContactType.MANAGEMENT,
                email="operations@trading-system.com",
                phone="+1-555-0104",
                preferred_channels=[NotificationChannel.EMAIL],
                escalation_delay_minutes=30
            ),
            EmergencyContact(
                id="backup-001",
                name="Backup Administrator",
                role="Secondary DevOps Engineer",
                contact_type=ContactType.SECONDARY,
                email="backup-admin@trading-system.com",
                phone="+1-555-0105",
                preferred_channels=[NotificationChannel.EMAIL, NotificationChannel.SMS],
                escalation_delay_minutes=20
            )
        ]

        for contact in default_contacts:
            self.contacts[contact.id] = contact

    def _initialize_templates(self):
        """Initialize notification templates for different scenarios"""
        templates = [
            NotificationTemplate(
                name="emergency_rollback",
                priority=NotificationPriority.EMERGENCY,
                channels=[NotificationChannel.EMAIL, NotificationChannel.SMS],
                subject_template="🚨 EMERGENCY ROLLBACK EXECUTED - {trigger_type}",
                body_template="""
EMERGENCY ROLLBACK NOTIFICATION
===============================

🚨 CRITICAL SYSTEM EVENT 🚨

System: TMT Automated Trading System
Event: Emergency Rollback to Cycle 4 Parameters
Trigger: {trigger_type}
Reason: {reason}
Timestamp: {timestamp}
Event ID: {event_id}

ROLLBACK STATUS:
- Previous Mode: {previous_mode}
- New Mode: {new_mode}
- Trading Status: STOPPED
- Validation Status: {validation_status}

SYSTEM IMPACT:
{system_impact}

IMMEDIATE ACTIONS REQUIRED:
1. ✅ Review system dashboard: http://localhost:3003
2. ✅ Verify system stability
3. ✅ Investigate root cause: {reason}
4. ✅ Contact technical team if assistance needed

RECOVERY VALIDATION:
{recovery_validation}

CONTACT INFORMATION:
- Dashboard: http://localhost:3003
- Orchestrator: http://localhost:8089/health
- Documentation: /docs/emergency-procedures.md

This is an automated emergency notification.
Response required within {escalation_delay_minutes} minutes.

⚠️ DO NOT IGNORE - System requires immediate attention
                """,
                include_attachments=True
            ),
            NotificationTemplate(
                name="automatic_trigger",
                priority=NotificationPriority.CRITICAL,
                channels=[NotificationChannel.EMAIL, NotificationChannel.SMS],
                subject_template="⚠️ AUTOMATIC ROLLBACK TRIGGER DETECTED - {trigger_type}",
                body_template="""
AUTOMATIC ROLLBACK TRIGGER ALERT
================================

⚠️ SYSTEM WARNING ⚠️

System: TMT Automated Trading System
Alert: Automatic Rollback Conditions Detected
Trigger: {trigger_type}
Threshold Breached: {threshold_details}
Consecutive Detections: {consecutive_count}
Timestamp: {timestamp}

PERFORMANCE METRICS:
{performance_metrics}

SYSTEM STATUS:
- Trading: {trading_status}
- Monitoring: Active
- Next Check: {next_check_time}

ACTION REQUIRED:
- If conditions persist, automatic rollback will execute
- Manual intervention may be needed
- Review performance dashboard immediately

Dashboard: http://localhost:3003
Monitoring: http://localhost:8089/rollback-monitor/status

Automatic rollback will execute if conditions continue.
                """
            ),
            NotificationTemplate(
                name="validation_failure",
                priority=NotificationPriority.HIGH,
                channels=[NotificationChannel.EMAIL],
                subject_template="❌ ROLLBACK VALIDATION FAILED - {event_id}",
                body_template="""
ROLLBACK VALIDATION FAILURE
===========================

❌ VALIDATION FAILED ❌

Event ID: {event_id}
Validation Score: {validation_score}/100
Failed Validations: {failed_validations}
Status: {validation_status}
Timestamp: {timestamp}

FAILED CHECKS:
{validation_details}

RECOMMENDATIONS:
{recommendations}

IMMEDIATE ACTIONS:
1. Review failed validation details
2. Manually verify system configuration
3. Restart affected services if needed
4. Re-run validation once issues resolved

System may not have fully recovered from rollback.
Manual intervention required.
                """
            ),
            NotificationTemplate(
                name="recovery_confirmed",
                priority=NotificationPriority.MEDIUM,
                channels=[NotificationChannel.EMAIL],
                subject_template="✅ SYSTEM RECOVERY CONFIRMED - {event_id}",
                body_template="""
SYSTEM RECOVERY CONFIRMATION
============================

✅ RECOVERY SUCCESSFUL ✅

Event ID: {event_id}
Validation Score: {validation_score}/100
Recovery Status: CONFIRMED
Timestamp: {timestamp}

VALIDATION RESULTS:
{validation_summary}

SYSTEM STATUS:
- Parameters: Cycle 4 Universal (Confirmed)
- Trading: Ready for Resume
- Agents: All Healthy
- Risk Controls: Active

NEXT STEPS:
1. ✅ System successfully rolled back to Cycle 4
2. ✅ All validations passed
3. ✅ Trading can be safely resumed
4. 📋 Investigate original issue cause
5. 📋 Plan remediation if needed

Recovery completed successfully.
System is stable and ready for operation.
                """
            )
        ]

        for template in templates:
            self.templates[template.name] = template

    async def notify_emergency_contacts(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.EMERGENCY,
        contact_types: List[ContactType] = None
    ) -> List[NotificationResult]:
        """
        Send emergency notifications to appropriate contacts

        Args:
            event_type: Type of emergency event
            event_data: Event data for template population
            priority: Notification priority level
            contact_types: Specific contact types to notify (optional)

        Returns:
            List of notification results
        """

        if contact_types is None:
            contact_types = [ContactType.PRIMARY, ContactType.TECHNICAL]

        logger.info(f"📧 Sending emergency notifications: {event_type}")
        logger.info(f"Priority: {priority.value}, Contact types: {[ct.value for ct in contact_types]}")

        # Get template for event type
        template = self.templates.get(event_type)
        if not template:
            logger.warning(f"No template found for event type: {event_type}")
            template = self._create_generic_template(event_type, priority)

        # Get contacts to notify
        contacts_to_notify = [
            contact for contact in self.contacts.values()
            if contact.active and contact.contact_type in contact_types
        ]

        if not contacts_to_notify:
            logger.warning(f"No active contacts found for types: {contact_types}")
            return []

        # Send notifications
        notification_results = []
        for contact in contacts_to_notify:
            try:
                contact_results = await self._notify_contact(contact, template, event_data)
                notification_results.extend(contact_results)
            except Exception as e:
                logger.error(f"Failed to notify contact {contact.id}: {e}")
                notification_results.append(NotificationResult(
                    contact_id=contact.id,
                    channel=NotificationChannel.EMAIL,  # Default channel
                    success=False,
                    timestamp=datetime.now(timezone.utc),
                    error_message=str(e)
                ))

        # Log notification summary
        successful = sum(1 for r in notification_results if r.success)
        total = len(notification_results)
        logger.info(f"✅ Notifications sent: {successful}/{total} successful")

        # Store notification history
        self.notification_history.append({
            "event_type": event_type,
            "priority": priority.value,
            "contacts_targeted": len(contacts_to_notify),
            "notifications_sent": total,
            "successful_notifications": successful,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": [asdict(result) for result in notification_results]
        })

        return notification_results

    async def _notify_contact(
        self,
        contact: EmergencyContact,
        template: NotificationTemplate,
        event_data: Dict[str, Any]
    ) -> List[NotificationResult]:
        """Send notification to a specific contact via their preferred channels"""

        results = []
        channels = contact.preferred_channels or [NotificationChannel.EMAIL]

        for channel in channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    result = await self._send_email(contact, template, event_data)
                elif channel == NotificationChannel.SMS:
                    result = await self._send_sms(contact, template, event_data)
                elif channel == NotificationChannel.SLACK:
                    result = await self._send_slack(contact, template, event_data)
                elif channel == NotificationChannel.TEAMS:
                    result = await self._send_teams(contact, template, event_data)
                else:
                    result = NotificationResult(
                        contact_id=contact.id,
                        channel=channel,
                        success=False,
                        timestamp=datetime.now(timezone.utc),
                        error_message=f"Unsupported channel: {channel.value}"
                    )

                results.append(result)

            except Exception as e:
                logger.error(f"Failed to send {channel.value} to {contact.id}: {e}")
                results.append(NotificationResult(
                    contact_id=contact.id,
                    channel=channel,
                    success=False,
                    timestamp=datetime.now(timezone.utc),
                    error_message=str(e)
                ))

        return results

    async def _send_email(
        self,
        contact: EmergencyContact,
        template: NotificationTemplate,
        event_data: Dict[str, Any]
    ) -> NotificationResult:
        """Send email notification"""

        try:
            if not contact.email:
                raise ValueError(f"No email address for contact {contact.id}")

            # Format message content
            subject = template.subject_template.format(**event_data)
            body = template.body_template.format(**event_data)

            # Create email message
            message = MIMEMultipart()
            message["From"] = formataddr(("TMT Trading System", self.email_config["username"]))
            message["To"] = formataddr((contact.name, contact.email))
            message["Subject"] = subject
            message["X-Priority"] = self._get_email_priority(template.priority)

            # Add body
            message.attach(MIMEText(body, "plain"))

            # Add attachments if requested
            if template.include_attachments:
                await self._add_email_attachments(message, event_data)

            # Send email (mock implementation for security)
            # In production, this would use actual SMTP configuration
            logger.info(f"📧 [MOCK] Email sent to {contact.email}")
            logger.info(f"Subject: {subject}")

            # TODO: Implement actual email sending
            # with smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"]) as server:
            #     if self.email_config["use_tls"]:
            #         server.starttls()
            #     server.login(self.email_config["username"], self.email_config["password"])
            #     server.send_message(message)

            return NotificationResult(
                contact_id=contact.id,
                channel=NotificationChannel.EMAIL,
                success=True,
                timestamp=datetime.now(timezone.utc),
                delivery_id=f"email_{contact.id}_{int(datetime.now().timestamp())}"
            )

        except Exception as e:
            logger.error(f"Email send failed for {contact.id}: {e}")
            return NotificationResult(
                contact_id=contact.id,
                channel=NotificationChannel.EMAIL,
                success=False,
                timestamp=datetime.now(timezone.utc),
                error_message=str(e)
            )

    async def _send_sms(
        self,
        contact: EmergencyContact,
        template: NotificationTemplate,
        event_data: Dict[str, Any]
    ) -> NotificationResult:
        """Send SMS notification"""

        try:
            if not contact.phone:
                raise ValueError(f"No phone number for contact {contact.id}")

            # Create short SMS message
            sms_message = f"TMT ALERT: {template.subject_template.format(**event_data)[:100]}... Check email for details."

            # Mock SMS sending
            logger.info(f"📱 [MOCK] SMS sent to {contact.phone}")
            logger.info(f"Message: {sms_message}")

            # TODO: Implement actual SMS sending (e.g., Twilio, AWS SNS)
            # sms_client.send_message(to=contact.phone, body=sms_message)

            return NotificationResult(
                contact_id=contact.id,
                channel=NotificationChannel.SMS,
                success=True,
                timestamp=datetime.now(timezone.utc),
                delivery_id=f"sms_{contact.id}_{int(datetime.now().timestamp())}"
            )

        except Exception as e:
            logger.error(f"SMS send failed for {contact.id}: {e}")
            return NotificationResult(
                contact_id=contact.id,
                channel=NotificationChannel.SMS,
                success=False,
                timestamp=datetime.now(timezone.utc),
                error_message=str(e)
            )

    async def _send_slack(
        self,
        contact: EmergencyContact,
        template: NotificationTemplate,
        event_data: Dict[str, Any]
    ) -> NotificationResult:
        """Send Slack notification"""

        try:
            if not contact.slack_user_id:
                raise ValueError(f"No Slack user ID for contact {contact.id}")

            # Format Slack message
            slack_message = {
                "channel": f"@{contact.slack_user_id}",
                "text": template.subject_template.format(**event_data),
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{template.subject_template.format(**event_data)}*"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": template.body_template.format(**event_data)[:2000]  # Slack limit
                        }
                    }
                ]
            }

            # Mock Slack sending
            logger.info(f"📢 [MOCK] Slack message sent to {contact.slack_user_id}")

            # TODO: Implement actual Slack sending
            # slack_client.chat_postMessage(**slack_message)

            return NotificationResult(
                contact_id=contact.id,
                channel=NotificationChannel.SLACK,
                success=True,
                timestamp=datetime.now(timezone.utc),
                delivery_id=f"slack_{contact.id}_{int(datetime.now().timestamp())}"
            )

        except Exception as e:
            logger.error(f"Slack send failed for {contact.id}: {e}")
            return NotificationResult(
                contact_id=contact.id,
                channel=NotificationChannel.SLACK,
                success=False,
                timestamp=datetime.now(timezone.utc),
                error_message=str(e)
            )

    async def _send_teams(
        self,
        contact: EmergencyContact,
        template: NotificationTemplate,
        event_data: Dict[str, Any]
    ) -> NotificationResult:
        """Send Microsoft Teams notification"""

        try:
            if not contact.teams_user_id:
                raise ValueError(f"No Teams user ID for contact {contact.id}")

            # Mock Teams sending
            logger.info(f"👥 [MOCK] Teams message sent to {contact.teams_user_id}")

            # TODO: Implement actual Teams sending
            # teams_client.send_message(...)

            return NotificationResult(
                contact_id=contact.id,
                channel=NotificationChannel.TEAMS,
                success=True,
                timestamp=datetime.now(timezone.utc),
                delivery_id=f"teams_{contact.id}_{int(datetime.now().timestamp())}"
            )

        except Exception as e:
            logger.error(f"Teams send failed for {contact.id}: {e}")
            return NotificationResult(
                contact_id=contact.id,
                channel=NotificationChannel.TEAMS,
                success=False,
                timestamp=datetime.now(timezone.utc),
                error_message=str(e)
            )

    async def _add_email_attachments(self, message: MIMEMultipart, event_data: Dict[str, Any]):
        """Add relevant attachments to email notifications"""
        # TODO: Add system logs, performance reports, etc.
        pass

    def _get_email_priority(self, priority: NotificationPriority) -> str:
        """Get email priority header value"""
        priority_map = {
            NotificationPriority.LOW: "5",
            NotificationPriority.MEDIUM: "3",
            NotificationPriority.HIGH: "2",
            NotificationPriority.CRITICAL: "1",
            NotificationPriority.EMERGENCY: "1"
        }
        return priority_map.get(priority, "3")

    def _create_generic_template(self, event_type: str, priority: NotificationPriority) -> NotificationTemplate:
        """Create generic template for unknown event types"""
        return NotificationTemplate(
            name=f"generic_{event_type}",
            priority=priority,
            channels=[NotificationChannel.EMAIL],
            subject_template=f"TMT Trading System Alert - {event_type}",
            body_template="""
Trading System Alert
===================

Event Type: {event_type}
Timestamp: {timestamp}
Details: {details}

Please check the system dashboard for more information.
Dashboard: http://localhost:3003
            """
        )

    def get_contacts(self) -> Dict[str, Dict[str, Any]]:
        """Get all emergency contacts"""
        return {
            contact_id: asdict(contact)
            for contact_id, contact in self.contacts.items()
        }

    def add_contact(self, contact: EmergencyContact) -> bool:
        """Add new emergency contact"""
        try:
            self.contacts[contact.id] = contact
            logger.info(f"✅ Emergency contact added: {contact.id} ({contact.name})")
            return True
        except Exception as e:
            logger.error(f"Failed to add contact {contact.id}: {e}")
            return False

    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> bool:
        """Update emergency contact information"""
        try:
            if contact_id not in self.contacts:
                raise ValueError(f"Contact {contact_id} not found")

            contact = self.contacts[contact_id]
            for key, value in updates.items():
                if hasattr(contact, key):
                    setattr(contact, key, value)

            logger.info(f"✅ Emergency contact updated: {contact_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update contact {contact_id}: {e}")
            return False

    def get_notification_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent notification history"""
        return sorted(
            self.notification_history,
            key=lambda x: x["timestamp"],
            reverse=True
        )[:limit]


# Global emergency contact system
emergency_contact_system: Optional[EmergencyContactSystem] = None

def get_emergency_contact_system() -> EmergencyContactSystem:
    """Get or create the global emergency contact system"""
    global emergency_contact_system
    if emergency_contact_system is None:
        emergency_contact_system = EmergencyContactSystem()
    return emergency_contact_system