/**
 * Agent Activity Stream API
 * Provides Server-Sent Events for real-time agent activity
 * Story 7.3: AC4 - Real-Time Agent Activity Feed WebSocket
 */

import { NextRequest } from 'next/server';
import { AgentActivityEvent, AI_AGENTS } from '@/types/intelligence';

// Force dynamic rendering
export const dynamic = 'force-dynamic';

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://localhost:8089';

/**
 * Generate mock agent activity events for development
 */
function generateMockEvent(): AgentActivityEvent {
  const agents = AI_AGENTS;
  const agent = agents[Math.floor(Math.random() * agents.length)];

  const symbols = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CHF'];
  const symbol = symbols[Math.floor(Math.random() * symbols.length)];

  const actions: Array<'BUY' | 'SELL' | 'NEUTRAL'> = ['BUY', 'SELL', 'NEUTRAL'];
  const action = actions[Math.floor(Math.random() * actions.length)];

  const eventTypes: AgentActivityEvent['eventType'][] = [
    'signal_generated',
    'trade_executed',
    'pattern_detected',
    'disagreement_resolved',
    'threshold_not_met'
  ];
  const eventType = eventTypes[Math.floor(Math.random() * eventTypes.length)];

  const confidence = 60 + Math.floor(Math.random() * 40); // 60-100

  const reasoningOptions: { [key: string]: string[][] } = {
    signal_generated: [
      ['Strong bullish momentum detected', 'Resistance break confirmed'],
      ['Bearish divergence forming', 'Volume declining at highs'],
      ['Support level holding', 'Bullish candlestick pattern']
    ],
    trade_executed: [
      ['Entry conditions met', 'Stop-loss and take-profit placed'],
      ['Filled at market price', 'Position size calculated']
    ],
    pattern_detected: [
      ['Wyckoff accumulation Phase E', 'Sign of Strength confirmed'],
      ['Distribution schematic detected', 'Upthrust after distribution'],
      ['Spring pattern forming', 'Support test successful']
    ],
    disagreement_resolved: [
      ['Consensus reached at 75%', 'Majority favors BUY signal'],
      ['Disagreement resolved', '6 of 8 agents agree']
    ],
    threshold_not_met: [
      ['Confidence below 70% threshold', 'Signal rejected'],
      ['Insufficient consensus', 'Only 55% agreement']
    ]
  };

  const reasoning = reasoningOptions[eventType][
    Math.floor(Math.random() * reasoningOptions[eventType].length)
  ];

  const metadata: AgentActivityEvent['metadata'] = {};

  if (eventType === 'disagreement_resolved') {
    metadata.consensusPercentage = 70 + Math.floor(Math.random() * 30);
  }

  if (eventType === 'pattern_detected') {
    const patterns = ['wyckoff-accumulation', 'wyckoff-distribution', 'spring', 'upthrust'];
    metadata.patternType = patterns[Math.floor(Math.random() * patterns.length)];
  }

  if (eventType === 'trade_executed') {
    metadata.tradeId = `trade-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    metadata.pnl = (Math.random() - 0.4) * 200; // Slight positive bias
  }

  const sessions = ['London', 'NY', 'Tokyo', 'Sydney'];
  metadata.sessionContext = sessions[Math.floor(Math.random() * sessions.length)];

  return {
    eventId: `evt-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    eventType,
    timestamp: Date.now(),
    agentId: agent.id,
    agentName: agent.name,
    symbol,
    action,
    confidence,
    reasoning,
    metadata
  };
}

/**
 * Fetch real agent activity from orchestrator
 */
async function fetchAgentActivity(): Promise<AgentActivityEvent[]> {
  try {
    // Try to fetch from orchestrator
    const response = await fetch(`${ORCHESTRATOR_URL}/agent-activity`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      signal: AbortSignal.timeout(3000)
    });

    if (response.ok) {
      const data = await response.json();
      return data.events || [];
    }
  } catch {
    // Orchestrator endpoint not available, will use mock data
    console.log('Agent activity endpoint not available, using mock data');
  }

  // Generate 1-3 mock events
  const eventCount = Math.random() < 0.7 ? 1 : Math.random() < 0.9 ? 2 : 3;
  const events: AgentActivityEvent[] = [];

  for (let i = 0; i < eventCount; i++) {
    events.push(generateMockEvent());
  }

  return events;
}

/**
 * GET /api/agent-activity
 * Server-Sent Events stream for real-time agent activity
 */
export async function GET(request: NextRequest) {
  const encoder = new TextEncoder();
  let isClosed = false;
  let interval: NodeJS.Timeout | null = null;

  const customReadable = new ReadableStream({
    start(controller) {
      // Helper function to safely enqueue data
      const safeEnqueue = (data: string) => {
        if (!isClosed) {
          try {
            controller.enqueue(encoder.encode(data));
          } catch (err) {
            console.warn('Failed to enqueue data, stream likely closed:', err);
            isClosed = true;
            if (interval) {
              clearInterval(interval);
              interval = null;
            }
          }
        }
      };

      // Send initial connection message
      safeEnqueue(`data: ${JSON.stringify({
        type: 'connected',
        timestamp: Date.now(),
        message: 'Agent activity stream connected'
      })}\n\n`);

      // Set up periodic updates - emit events every 3-8 seconds (realistic rate)
      const scheduleNextEvent = () => {
        if (isClosed) return;

        const delay = 3000 + Math.random() * 5000; // 3-8 seconds

        interval = setTimeout(async () => {
          if (isClosed) {
            if (interval) {
              clearTimeout(interval);
              interval = null;
            }
            return;
          }

          try {
            // Fetch or generate events
            const events = await fetchAgentActivity();

            // Send each event
            for (const event of events) {
              if (!isClosed) {
                safeEnqueue(`data: ${JSON.stringify(event)}\n\n`);

                // Small delay between events if multiple
                if (events.length > 1) {
                  await new Promise(resolve => setTimeout(resolve, 100));
                }
              }
            }

            // Schedule next event
            scheduleNextEvent();

          } catch (err) {
            if (!isClosed) {
              console.error('Agent activity stream error:', err);

              safeEnqueue(`data: ${JSON.stringify({
                type: 'error',
                timestamp: Date.now(),
                error: 'Failed to fetch agent activity'
              })}\n\n`);

              // Continue trying
              scheduleNextEvent();
            }
          }
        }, delay);
      };

      // Start the event loop
      scheduleNextEvent();

      // Cleanup on close
      const cleanup = () => {
        isClosed = true;
        if (interval) {
          clearTimeout(interval);
          interval = null;
        }
        try {
          controller.close();
        } catch {
          // Already closed, ignore
        }
      };

      request.signal?.addEventListener('abort', cleanup);

      // Also listen for client disconnect
      setTimeout(() => {
        if (request.signal?.aborted) {
          cleanup();
        }
      }, 100);
    },

    cancel() {
      isClosed = true;
      if (interval) {
        clearTimeout(interval);
        interval = null;
      }
    }
  });

  return new Response(customReadable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET',
      'Access-Control-Allow-Headers': 'Cache-Control'
    }
  });
}
