"""
Database migration management system.

Provides functionality for tracking and applying database schema migrations
with version control and rollback support.
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class MigrationManager:
    """
    Database migration manager with version tracking.

    Manages sequential database migrations with SHA256 checksums
    to ensure migration integrity.
    """

    def __init__(self, engine: AsyncEngine, migrations_dir: Path = None):
        """
        Initialize migration manager.

        Args:
            engine: Async SQLAlchemy engine
            migrations_dir: Directory containing migration SQL files
        """
        self.engine = engine
        self.migrations_dir = migrations_dir or (
            Path(__file__).parent / "migrations"
        )

    async def create_migration_table(self) -> None:
        """
        Create migration_history table if it doesn't exist.

        Table schema:
        - version: INTEGER PRIMARY KEY - Migration version number
        - name: TEXT - Migration file name
        - applied_at: TIMESTAMP - When migration was applied
        - checksum: TEXT - SHA256 checksum of migration file
        """
        async with self.engine.begin() as conn:
            await conn.execute(
                text("""
                    CREATE TABLE IF NOT EXISTS migration_history (
                        version INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        applied_at TIMESTAMP NOT NULL,
                        checksum TEXT NOT NULL
                    )
                """)
            )
        logger.info("Migration history table created/verified")

    async def get_current_version(self) -> int:
        """
        Get the current database schema version.

        Returns:
            int: Current version number (0 if no migrations applied)
        """
        try:
            await self.create_migration_table()

            async with self.engine.begin() as conn:
                result = await conn.execute(
                    text("SELECT MAX(version) as max_version FROM migration_history")
                )
                row = result.fetchone()
                version = row[0] if row and row[0] is not None else 0

            logger.info(f"Current database version: {version}")
            return version

        except Exception as e:
            logger.error(f"Error getting current version: {e}")
            return 0

    async def get_migration_files(self) -> List[Tuple[int, Path]]:
        """
        Get all migration SQL files sorted by version number.

        Returns:
            List[Tuple[int, Path]]: List of (version, file_path) tuples
        """
        migrations = []

        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return migrations

        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            # Extract version number from filename (e.g., "001_initial.sql" -> 1)
            try:
                version = int(file_path.stem.split("_")[0])
                migrations.append((version, file_path))
            except (ValueError, IndexError) as e:
                logger.warning(f"Invalid migration filename: {file_path.name} - {e}")
                continue

        migrations.sort(key=lambda x: x[0])
        logger.info(f"Found {len(migrations)} migration files")

        return migrations

    def calculate_checksum(self, file_path: Path) -> str:
        """
        Calculate SHA256 checksum of migration file.

        Args:
            file_path: Path to migration SQL file

        Returns:
            str: Hex digest of SHA256 checksum
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    async def apply_migration(self, version: int, file_path: Path) -> None:
        """
        Apply a single migration file to the database.

        Args:
            version: Migration version number
            file_path: Path to migration SQL file

        Raises:
            Exception: If migration application fails
        """
        logger.info(f"Applying migration {version}: {file_path.name}")

        # Read migration SQL
        with open(file_path, "r", encoding="utf-8") as f:
            migration_sql = f.read()

        # Calculate checksum
        checksum = self.calculate_checksum(file_path)

        # Execute migration within a transaction
        async with self.engine.begin() as conn:
            # Execute migration SQL
            # Split on semicolons to execute multiple statements
            statements = [s.strip() for s in migration_sql.split(";") if s.strip()]

            for statement in statements:
                if statement:
                    await conn.execute(text(statement))

            # Record migration in history
            await conn.execute(
                text("""
                    INSERT INTO migration_history (version, name, applied_at, checksum)
                    VALUES (:version, :name, :applied_at, :checksum)
                """),
                {
                    "version": version,
                    "name": file_path.name,
                    "applied_at": datetime.now(timezone.utc),
                    "checksum": checksum,
                },
            )

        logger.info(f"✅ Successfully applied migration {version}: {file_path.name}")

    async def run_migrations(self) -> int:
        """
        Run all pending database migrations.

        Returns:
            int: Number of migrations applied

        Raises:
            Exception: If any migration fails
        """
        logger.info("Starting migration process...")

        # Ensure migration table exists
        await self.create_migration_table()

        # Get current version
        current_version = await self.get_current_version()

        # Get all migration files
        migration_files = await self.get_migration_files()

        # Filter to unapplied migrations
        pending_migrations = [
            (version, file_path)
            for version, file_path in migration_files
            if version > current_version
        ]

        if not pending_migrations:
            logger.info("No pending migrations to apply")
            return 0

        logger.info(f"Found {len(pending_migrations)} pending migrations")

        # Apply each migration in order
        applied_count = 0
        for version, file_path in pending_migrations:
            try:
                await self.apply_migration(version, file_path)
                applied_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to apply migration {version}: {e}")
                logger.error(f"Migration process stopped. Applied {applied_count} migrations.")
                raise

        logger.info(f"✅ Successfully applied {applied_count} migrations")
        return applied_count

    async def verify_migrations(self) -> bool:
        """
        Verify integrity of applied migrations by checking checksums.

        Returns:
            bool: True if all migrations match their checksums, False otherwise
        """
        logger.info("Verifying migration integrity...")

        # Get current version
        current_version = await self.get_current_version()

        if current_version == 0:
            logger.info("No migrations to verify")
            return True

        # Get migration history from database
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text("""
                    SELECT version, name, checksum
                    FROM migration_history
                    ORDER BY version
                """)
            )
            db_migrations = result.fetchall()

        # Verify each migration
        all_valid = True
        for version, name, db_checksum in db_migrations:
            file_path = self.migrations_dir / name

            if not file_path.exists():
                logger.error(f"❌ Migration file missing: {name}")
                all_valid = False
                continue

            file_checksum = self.calculate_checksum(file_path)

            if file_checksum != db_checksum:
                logger.error(
                    f"❌ Checksum mismatch for migration {version}: {name}"
                )
                logger.error(f"   Expected: {db_checksum}")
                logger.error(f"   Got: {file_checksum}")
                all_valid = False
            else:
                logger.info(f"✅ Migration {version} verified: {name}")

        if all_valid:
            logger.info("✅ All migrations verified successfully")
        else:
            logger.error("❌ Migration verification failed")

        return all_valid
