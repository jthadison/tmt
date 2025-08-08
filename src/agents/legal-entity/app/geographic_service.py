"""Geographic restriction enforcement and jurisdiction management."""

import ipaddress
from datetime import datetime, time
from typing import Dict, List, Optional, Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models import (
    GeographicRestriction, LegalEntity,
    JurisdictionRestriction, GeographicRestrictionConfig
)


class GeographicService:
    """Manages geographic restrictions and jurisdiction compliance."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.restricted_jurisdictions = {
            # Sanctioned countries (OFAC)
            "IR": JurisdictionRestriction.PROHIBITED,  # Iran
            "KP": JurisdictionRestriction.PROHIBITED,  # North Korea
            "SY": JurisdictionRestriction.PROHIBITED,  # Syria
            "CU": JurisdictionRestriction.PROHIBITED,  # Cuba
            
            # Restricted jurisdictions
            "US-NY": JurisdictionRestriction.RESTRICTED,  # New York (BitLicense)
            "US-WA": JurisdictionRestriction.RESTRICTED,  # Washington
            "CN": JurisdictionRestriction.RESTRICTED,     # China
            "IN": JurisdictionRestriction.RESTRICTED,     # India
            
            # Special regulations
            "EU": JurisdictionRestriction.ALLOWED,  # MiFID II compliance required
            "UK": JurisdictionRestriction.ALLOWED,  # FCA compliance required
            "JP": JurisdictionRestriction.ALLOWED,  # JFSA compliance required
        }
        
        self.trading_hours = {
            "US": {"open": time(9, 30), "close": time(16, 0), "timezone": "America/New_York"},
            "UK": {"open": time(8, 0), "close": time(16, 30), "timezone": "Europe/London"},
            "EU": {"open": time(9, 0), "close": time(17, 30), "timezone": "Europe/Frankfurt"},
            "JP": {"open": time(9, 0), "close": time(15, 0), "timezone": "Asia/Tokyo"},
            "AU": {"open": time(10, 0), "close": time(16, 0), "timezone": "Australia/Sydney"}
        }
        
        self.holidays_2025 = {
            "US": [
                datetime(2025, 1, 1),   # New Year's Day
                datetime(2025, 1, 20),  # MLK Day
                datetime(2025, 2, 17),  # Presidents Day
                datetime(2025, 4, 18),  # Good Friday
                datetime(2025, 5, 26),  # Memorial Day
                datetime(2025, 7, 4),   # Independence Day
                datetime(2025, 9, 1),   # Labor Day
                datetime(2025, 11, 27), # Thanksgiving
                datetime(2025, 12, 25), # Christmas
            ],
            "UK": [
                datetime(2025, 1, 1),   # New Year's Day
                datetime(2025, 4, 18),  # Good Friday
                datetime(2025, 4, 21),  # Easter Monday
                datetime(2025, 5, 5),   # Early May Bank Holiday
                datetime(2025, 5, 26),  # Spring Bank Holiday
                datetime(2025, 8, 25),  # Summer Bank Holiday
                datetime(2025, 12, 25), # Christmas
                datetime(2025, 12, 26), # Boxing Day
            ]
        }
    
    async def check_jurisdiction_access(
        self,
        entity_id: UUID,
        ip_address: str
    ) -> Dict[str, Any]:
        """Check if access is allowed from the given IP address."""
        entity = self.db.query(LegalEntity).filter(
            LegalEntity.entity_id == entity_id
        ).first()
        
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")
        
        # Get jurisdiction from IP (simplified - would use GeoIP database in production)
        jurisdiction = await self._get_jurisdiction_from_ip(ip_address)
        
        # Check if jurisdiction is restricted
        restriction_level = self.restricted_jurisdictions.get(
            jurisdiction,
            JurisdictionRestriction.ALLOWED
        )
        
        # Check entity's registered jurisdiction
        entity_jurisdiction = entity.jurisdiction
        if entity_jurisdiction != jurisdiction and restriction_level == JurisdictionRestriction.RESTRICTED:
            return {
                "allowed": False,
                "reason": f"Access restricted from {jurisdiction} for entity registered in {entity_jurisdiction}",
                "restriction_level": restriction_level.value,
                "detected_jurisdiction": jurisdiction,
                "entity_jurisdiction": entity_jurisdiction
            }
        
        if restriction_level == JurisdictionRestriction.PROHIBITED:
            return {
                "allowed": False,
                "reason": f"Access prohibited from sanctioned jurisdiction: {jurisdiction}",
                "restriction_level": restriction_level.value,
                "detected_jurisdiction": jurisdiction
            }
        
        # Check for VPN/Proxy
        is_vpn = await self._detect_vpn_proxy(ip_address)
        if is_vpn:
            return {
                "allowed": False,
                "reason": "VPN/Proxy detected - direct connection required",
                "restriction_level": "vpn_detected",
                "ip_address": ip_address
            }
        
        return {
            "allowed": True,
            "restriction_level": restriction_level.value,
            "detected_jurisdiction": jurisdiction,
            "entity_jurisdiction": entity_jurisdiction,
            "compliance_requirements": self._get_compliance_requirements(jurisdiction)
        }
    
    async def check_trading_hours(
        self,
        entity_id: UUID,
        target_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Check if trading is allowed at the given time."""
        entity = self.db.query(LegalEntity).filter(
            LegalEntity.entity_id == entity_id
        ).first()
        
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")
        
        jurisdiction = entity.jurisdiction
        check_time = target_time or datetime.utcnow()
        
        # Get trading hours for jurisdiction
        hours_config = self._get_trading_hours(jurisdiction)
        if not hours_config:
            return {
                "allowed": True,
                "reason": "No trading hour restrictions for jurisdiction",
                "jurisdiction": jurisdiction
            }
        
        # Convert to local timezone
        tz = ZoneInfo(hours_config["timezone"])
        local_time = check_time.astimezone(tz)
        
        # Check if it's a holiday
        if await self._is_holiday(jurisdiction, local_time.date()):
            return {
                "allowed": False,
                "reason": "Market closed - Holiday",
                "jurisdiction": jurisdiction,
                "date": local_time.date().isoformat()
            }
        
        # Check if it's a weekend
        if local_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return {
                "allowed": False,
                "reason": "Market closed - Weekend",
                "jurisdiction": jurisdiction,
                "day": local_time.strftime("%A")
            }
        
        # Check trading hours
        current_time = local_time.time()
        if current_time < hours_config["open"] or current_time > hours_config["close"]:
            return {
                "allowed": False,
                "reason": "Outside trading hours",
                "jurisdiction": jurisdiction,
                "current_time": current_time.isoformat(),
                "market_open": hours_config["open"].isoformat(),
                "market_close": hours_config["close"].isoformat(),
                "timezone": hours_config["timezone"]
            }
        
        return {
            "allowed": True,
            "jurisdiction": jurisdiction,
            "current_time": current_time.isoformat(),
            "market_open": hours_config["open"].isoformat(),
            "market_close": hours_config["close"].isoformat(),
            "timezone": hours_config["timezone"]
        }
    
    async def create_restriction(
        self,
        config: GeographicRestrictionConfig
    ) -> GeographicRestriction:
        """Create or update a geographic restriction."""
        existing = self.db.query(GeographicRestriction).filter(
            GeographicRestriction.jurisdiction == config.jurisdiction
        ).first()
        
        if existing:
            # Update existing restriction
            existing.restriction_level = config.restriction_level.value
            existing.trading_hours = config.trading_hours
            existing.holidays = [d.isoformat() for d in config.holidays] if config.holidays else None
            existing.regulatory_requirements = config.regulatory_requirements
            existing.updated_at = datetime.utcnow()
            restriction = existing
        else:
            # Create new restriction
            restriction = GeographicRestriction(
                jurisdiction=config.jurisdiction,
                restriction_level=config.restriction_level.value,
                trading_hours=config.trading_hours,
                holidays=[d.isoformat() for d in config.holidays] if config.holidays else None,
                regulatory_requirements=config.regulatory_requirements
            )
            self.db.add(restriction)
        
        self.db.commit()
        self.db.refresh(restriction)
        return restriction
    
    async def get_entity_restrictions(
        self,
        entity_id: UUID
    ) -> Dict[str, Any]:
        """Get all restrictions applicable to an entity."""
        entity = self.db.query(LegalEntity).filter(
            LegalEntity.entity_id == entity_id
        ).first()
        
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")
        
        jurisdiction = entity.jurisdiction
        
        # Get restriction from database
        restriction = self.db.query(GeographicRestriction).filter(
            GeographicRestriction.jurisdiction == jurisdiction
        ).first()
        
        if restriction:
            return {
                "entity_id": str(entity_id),
                "jurisdiction": jurisdiction,
                "restriction_level": restriction.restriction_level,
                "trading_hours": restriction.trading_hours,
                "holidays": restriction.holidays,
                "regulatory_requirements": restriction.regulatory_requirements
            }
        
        # Use default restrictions
        restriction_level = self.restricted_jurisdictions.get(
            jurisdiction,
            JurisdictionRestriction.ALLOWED
        )
        
        return {
            "entity_id": str(entity_id),
            "jurisdiction": jurisdiction,
            "restriction_level": restriction_level.value,
            "trading_hours": self._get_trading_hours(jurisdiction),
            "holidays": self.holidays_2025.get(jurisdiction, []),
            "regulatory_requirements": self._get_compliance_requirements(jurisdiction)
        }
    
    async def validate_multi_jurisdiction_compliance(
        self,
        entity_ids: List[UUID]
    ) -> Dict[str, Any]:
        """Validate compliance across multiple jurisdictions."""
        results = {}
        jurisdictions = set()
        
        for entity_id in entity_ids:
            entity = self.db.query(LegalEntity).filter(
                LegalEntity.entity_id == entity_id
            ).first()
            
            if entity:
                jurisdictions.add(entity.jurisdiction)
                restrictions = await self.get_entity_restrictions(entity_id)
                results[str(entity_id)] = {
                    "jurisdiction": entity.jurisdiction,
                    "compliant": restrictions["restriction_level"] != "prohibited",
                    "restrictions": restrictions
                }
        
        # Check for conflicts
        conflicts = []
        if len(jurisdictions) > 1:
            # Check for incompatible jurisdiction pairs
            if "US" in jurisdictions and "IR" in jurisdictions:
                conflicts.append("Cannot operate entities in both US and sanctioned countries")
            if "EU" in jurisdictions and "CN" in jurisdictions:
                conflicts.append("Special compliance required for EU-China operations")
        
        return {
            "total_entities": len(entity_ids),
            "jurisdictions": list(jurisdictions),
            "entity_compliance": results,
            "conflicts": conflicts,
            "multi_jurisdiction_compliant": len(conflicts) == 0
        }
    
    async def _get_jurisdiction_from_ip(self, ip_address: str) -> str:
        """Get jurisdiction from IP address (simplified implementation)."""
        # In production, would use MaxMind GeoIP or similar
        # This is a simplified mock implementation
        
        try:
            ip = ipaddress.ip_address(ip_address)
            
            # Mock IP ranges for demonstration
            if ip in ipaddress.ip_network("8.0.0.0/8"):
                return "US"
            elif ip in ipaddress.ip_network("81.0.0.0/8"):
                return "UK"
            elif ip in ipaddress.ip_network("85.0.0.0/8"):
                return "EU"
            elif ip in ipaddress.ip_network("1.0.0.0/8"):
                return "AU"
            elif ip in ipaddress.ip_network("14.0.0.0/8"):
                return "JP"
            else:
                return "UNKNOWN"
        except:
            return "UNKNOWN"
    
    async def _detect_vpn_proxy(self, ip_address: str) -> bool:
        """Detect if IP is from VPN or proxy (simplified)."""
        # In production, would use services like IPQualityScore or similar
        # This is a simplified mock implementation
        
        # Check for common VPN/datacenter IP ranges
        datacenter_ranges = [
            "104.0.0.0/8",   # Common VPN range
            "45.0.0.0/8",    # Common proxy range
            "23.0.0.0/8",    # Common datacenter range
        ]
        
        try:
            ip = ipaddress.ip_address(ip_address)
            for range_str in datacenter_ranges:
                if ip in ipaddress.ip_network(range_str):
                    return True
            return False
        except:
            return False
    
    async def _is_holiday(self, jurisdiction: str, check_date: datetime) -> bool:
        """Check if given date is a holiday in the jurisdiction."""
        holidays = self.holidays_2025.get(jurisdiction, [])
        return any(h.date() == check_date for h in holidays)
    
    def _get_trading_hours(self, jurisdiction: str) -> Optional[Dict[str, Any]]:
        """Get trading hours configuration for jurisdiction."""
        # Map specific jurisdictions to regions
        region_map = {
            "US": "US", "US-NY": "US", "US-CA": "US",
            "UK": "UK", "GB": "UK",
            "DE": "EU", "FR": "EU", "IT": "EU", "ES": "EU",
            "JP": "JP",
            "AU": "AU", "NZ": "AU"
        }
        
        region = region_map.get(jurisdiction, jurisdiction)
        return self.trading_hours.get(region)
    
    def _get_compliance_requirements(self, jurisdiction: str) -> Dict[str, Any]:
        """Get compliance requirements for jurisdiction."""
        requirements = {
            "US": {
                "regulations": ["CFTC", "NFA"],
                "reporting": "Required",
                "kyc_level": "Enhanced",
                "tax_reporting": "Form 1099"
            },
            "EU": {
                "regulations": ["MiFID II", "GDPR"],
                "reporting": "Transaction reporting",
                "kyc_level": "Standard",
                "tax_reporting": "Local requirements"
            },
            "UK": {
                "regulations": ["FCA"],
                "reporting": "Required",
                "kyc_level": "Standard",
                "tax_reporting": "HMRC requirements"
            },
            "JP": {
                "regulations": ["JFSA"],
                "reporting": "Required",
                "kyc_level": "Standard",
                "tax_reporting": "Local requirements"
            }
        }
        
        return requirements.get(jurisdiction, {
            "regulations": ["Local"],
            "reporting": "As required",
            "kyc_level": "Basic",
            "tax_reporting": "Local requirements"
        })


from uuid import UUID  # Add this import at the top