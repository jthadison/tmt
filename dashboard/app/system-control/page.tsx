'use client';

import React from 'react';
import EmergencyRollbackControl from '@/components/emergency/EmergencyRollbackControl';
import RollbackHistoryTable from '@/components/emergency/RollbackHistoryTable';
import AutomatedTriggerMonitoring from '@/components/emergency/AutomatedTriggerMonitoring';

export default function SystemControlPage() {
  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">System Control Panel</h1>
          <p className="text-gray-400">
            Manage emergency rollback controls, monitor automated triggers, and view system history
          </p>
        </div>

        {/* Emergency Rollback Control */}
        <section>
          <h2 className="text-2xl font-semibold text-white mb-4">
            Emergency Rollback Control
          </h2>
          <EmergencyRollbackControl />
        </section>

        {/* Rollback History */}
        <section>
          <h2 className="text-2xl font-semibold text-white mb-4">
            Rollback History
          </h2>
          <RollbackHistoryTable />
        </section>

        {/* Automated Trigger Monitoring */}
        <section>
          <h2 className="text-2xl font-semibold text-white mb-4">
            Automated Trigger Monitoring
          </h2>
          <AutomatedTriggerMonitoring />
        </section>
      </div>
    </div>
  );
}
