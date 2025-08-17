#!/bin/bash
# Container Security Setup Script
# This script configures security hardening for the broker integration container

set -euo pipefail

echo "Starting container security setup..."

# Create necessary directories with proper permissions
mkdir -p /app/logs /app/data /app/temp_retention /app/transaction_data
chown -R appuser:appgroup /app

# Set secure file permissions
find /app -type f -name "*.py" -exec chmod 644 {} \;
find /app -type f -name "*.sh" -exec chmod 755 {} \;
find /app -type d -exec chmod 755 {} \;

# Set specific permissions for sensitive directories
chmod 700 /app/data
chmod 700 /app/temp_retention  
chmod 700 /app/transaction_data
chmod 755 /app/logs

# Remove any world-writable permissions
find /app -type f -perm -002 -exec chmod g-w,o-w {} \;
find /app -type d -perm -002 -exec chmod g-w,o-w {} \;

# Secure Python cache directories
find /app -name "__pycache__" -type d -exec chmod 700 {} \; 2>/dev/null || true

# Set environment variables for security
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Verify no SUID/SGID files exist
echo "Checking for SUID/SGID files..."
SUID_FILES=$(find /app -type f \( -perm -4000 -o -perm -2000 \) 2>/dev/null || true)
if [ -n "$SUID_FILES" ]; then
    echo "WARNING: Found SUID/SGID files:"
    echo "$SUID_FILES"
else
    echo "No SUID/SGID files found - OK"
fi

# Verify user ownership
echo "Verifying file ownership..."
WRONG_OWNER=$(find /app ! -user appuser 2>/dev/null || true)
if [ -n "$WRONG_OWNER" ]; then
    echo "WARNING: Files not owned by appuser:"
    echo "$WRONG_OWNER"
    chown -R appuser:appgroup /app
fi

echo "Container security setup completed successfully"