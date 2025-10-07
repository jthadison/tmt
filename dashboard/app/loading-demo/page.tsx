/**
 * Loading States Demo Page
 * Story 9.1: Comprehensive demonstration of all loading states and skeleton screens
 */

'use client';

import { Suspense, useState } from 'react';
import { DashboardSkeleton, PositionCardSkeleton, ChartSkeleton, AgentCardSkeleton } from '@/components/skeletons';
import { InlineSpinner, ModalOverlay, ProgressBar } from '@/components/loading';
import { LoadingButton } from '@/components/buttons';
import { useSkeletonTimeout } from '@/hooks/useSkeletonTimeout';

// Simulated async component for Suspense demonstration
function AsyncContent() {
  return (
    <div className="bg-green-100 dark:bg-green-900 p-4 rounded-lg">
      <p className="text-green-800 dark:text-green-200 font-medium">
        Content loaded successfully!
      </p>
    </div>
  );
}

export default function LoadingDemoPage() {
  const [showModal, setShowModal] = useState(false);
  const [progress, setProgress] = useState(0);
  const [showTimeout, setShowTimeout] = useState(false);

  const { timedOut, reset } = useSkeletonTimeout({
    timeout: showTimeout ? 3000 : 30000, // 3s for demo, 30s normally
    onTimeout: () => console.log('Skeleton timed out!'),
  });

  // Simulate progress
  const startProgress = () => {
    setProgress(0);
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          return 100;
        }
        return prev + 10;
      });
    }, 300);
  };

  // Simulate modal operation
  const handleModalDemo = async () => {
    setShowModal(true);
    await new Promise((resolve) => setTimeout(resolve, 3000));
    setShowModal(false);
  };

  // Simulate button action
  const handleButtonAction = async () => {
    await new Promise((resolve) => setTimeout(resolve, 2000));
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Loading States Demo
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Story 9.1: Skeleton Screens & Loading Indicators
          </p>
        </div>

        {/* Skeleton Screens Section */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            1. Skeleton Screens
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                Position Card Skeleton
              </h3>
              <PositionCardSkeleton />
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                Agent Card Skeleton
              </h3>
              <AgentCardSkeleton />
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
              Chart Skeleton
            </h3>
            <ChartSkeleton />
          </div>
        </section>

        {/* Loading Indicators Section */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            2. Loading Indicators
          </h2>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 space-y-6">
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                Inline Spinners
              </h3>
              <div className="flex flex-wrap gap-4">
                <InlineSpinner size="sm" text="Small spinner" />
                <InlineSpinner size="md" text="Medium spinner" />
                <InlineSpinner size="lg" text="Large spinner" />
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                Progress Bar
              </h3>
              <button
                onClick={startProgress}
                className="mb-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Start Progress
              </button>
              <ProgressBar
                progress={progress}
                message={`Processing items... ${Math.round(progress)} of 100 complete`}
              />
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                Modal Overlay
              </h3>
              <button
                onClick={handleModalDemo}
                className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
              >
                Show Modal Overlay (3s)
              </button>
            </div>
          </div>
        </section>

        {/* Loading Button Section */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            3. Loading Button States
          </h2>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
            <div className="flex flex-wrap gap-4">
              <LoadingButton onClick={handleButtonAction} variant="primary">
                Primary Action
              </LoadingButton>
              <LoadingButton
                onClick={handleButtonAction}
                variant="secondary"
                successMessage="Completed!"
              >
                Secondary Action
              </LoadingButton>
              <LoadingButton
                onClick={handleButtonAction}
                variant="danger"
                successMessage="Deleted!"
              >
                Delete Item
              </LoadingButton>
            </div>
          </div>
        </section>

        {/* React Suspense Section */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            4. React Suspense Integration
          </h2>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 space-y-4">
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
              Async Content with Position Card Skeleton
            </h3>
            <Suspense fallback={<PositionCardSkeleton />}>
              <AsyncContent />
            </Suspense>
          </div>
        </section>

        {/* Skeleton Timeout Section */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            5. Skeleton Timeout (30s → Error State)
          </h2>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 space-y-4">
            <div className="flex gap-4">
              <button
                onClick={() => {
                  setShowTimeout(true);
                  reset();
                }}
                className="px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700"
              >
                Start 3s Timeout Demo
              </button>
              <button
                onClick={() => {
                  setShowTimeout(false);
                  reset();
                }}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Reset
              </button>
            </div>

            {showTimeout && !timedOut && <PositionCardSkeleton />}

            {timedOut && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <p className="text-red-800 dark:text-red-200 font-medium mb-2">
                  Unable to load data
                </p>
                <button
                  onClick={() => {
                    reset();
                    setShowTimeout(true);
                  }}
                  className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                >
                  Retry
                </button>
              </div>
            )}
          </div>
        </section>

        {/* Full Dashboard Skeleton */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            6. Full Dashboard Skeleton
          </h2>
          <div className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg overflow-hidden">
            <DashboardSkeleton />
          </div>
        </section>
      </div>

      {/* Modal Overlay */}
      <ModalOverlay
        isOpen={showModal}
        message="Processing your request... Please wait."
      />
    </div>
  );
}
