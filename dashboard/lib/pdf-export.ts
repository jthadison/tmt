/**
 * PDF Export Utility - Story 11.8, Task 10
 *
 * Exports walk-forward validation reports to PDF
 */

import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import type { WalkForwardReport } from '@/types/validation';

export interface PDFExportOptions {
  includeCharts?: boolean;
  includeDetailedWindows?: boolean;
  format?: 'portrait' | 'landscape';
}

export class ValidationReportPDFExporter {
  private doc: jsPDF;

  constructor(format: 'portrait' | 'landscape' = 'portrait') {
    this.doc = new jsPDF({
      orientation: format,
      unit: 'mm',
      format: 'a4',
    });
  }

  /**
   * Export walk-forward report to PDF
   */
  async exportWalkForwardReport(
    report: WalkForwardReport,
    options: PDFExportOptions = {}
  ): Promise<void> {
    const { includeCharts = true, includeDetailedWindows = true } = options;

    // Page 1: Header and Summary
    this.addHeader(report);
    this.addSummaryMetrics(report);

    // Page 2: Session Performance
    this.doc.addPage();
    this.addSessionPerformance(report);

    // Page 3: Parameter Stability
    this.doc.addPage();
    this.addParameterStability(report);

    // Optional: Detailed windows
    if (includeDetailedWindows && report.windows.length > 0) {
      this.doc.addPage();
      this.addWindows(report);
    }

    // Footer on all pages
    this.addFooters();

    // Download
    this.doc.save(`validation-report-${report.job_id}.pdf`);
  }

  private addHeader(report: WalkForwardReport) {
    // Title
    this.doc.setFontSize(20);
    this.doc.setFont('helvetica', 'bold');
    this.doc.text('Walk-Forward Validation Report', 20, 20);

    // Metadata
    this.doc.setFontSize(10);
    this.doc.setFont('helvetica', 'normal');
    this.doc.text(`Job ID: ${report.job_id}`, 20, 30);
    this.doc.text(`Config: ${report.config_file}`, 20, 35);
    this.doc.text(`Generated: ${new Date(report.timestamp).toLocaleString()}`, 20, 40);
    this.doc.text(`Status: ${report.status}`, 20, 45);

    // Separator line
    this.doc.setLineWidth(0.5);
    this.doc.line(20, 50, 190, 50);
  }

  private addSummaryMetrics(report: WalkForwardReport) {
    let y = 60;

    this.doc.setFontSize(14);
    this.doc.setFont('helvetica', 'bold');
    this.doc.text('Summary Metrics', 20, y);

    y += 10;
    this.doc.setFontSize(10);
    this.doc.setFont('helvetica', 'normal');

    const metrics = [
      ['Average In-Sample Sharpe:', report.avg_in_sample_sharpe.toFixed(3)],
      ['Average Out-of-Sample Sharpe:', report.avg_out_of_sample_sharpe.toFixed(3)],
      ['Overfitting Score:', report.overfitting_score.toFixed(3)],
      ['Degradation Factor:', report.degradation_factor.toFixed(3)],
      [
        'Performance Degradation:',
        `${((1 - report.degradation_factor) * 100).toFixed(1)}%`,
      ],
    ];

    metrics.forEach(([label, value]) => {
      this.doc.text(label, 20, y);
      this.doc.setFont('helvetica', 'bold');
      this.doc.text(value, 120, y);
      this.doc.setFont('helvetica', 'normal');
      y += 7;
    });

    // Overfitting assessment
    y += 5;
    this.doc.setFontSize(12);
    this.doc.setFont('helvetica', 'bold');

    const score = report.overfitting_score;
    const assessment =
      score < 0.3
        ? { text: 'Assessment: PASSED ✓', color: [0, 128, 0] }
        : score < 0.5
          ? { text: 'Assessment: WARNING ⚠', color: [255, 165, 0] }
          : { text: 'Assessment: FAILED ✗', color: [255, 0, 0] };

    this.doc.setTextColor(...assessment.color);
    this.doc.text(assessment.text, 20, y);
    this.doc.setTextColor(0, 0, 0);
  }

  private addSessionPerformance(report: WalkForwardReport) {
    this.doc.setFontSize(14);
    this.doc.setFont('helvetica', 'bold');
    this.doc.text('Performance by Trading Session', 20, 20);

    // Table header
    const startY = 30;
    const colWidths = [40, 30, 30, 30, 30];
    const headers = ['Session', 'Sharpe', 'Win Rate', 'P.Factor', 'Trades'];

    this.doc.setFontSize(9);
    this.doc.setFont('helvetica', 'bold');

    let x = 20;
    headers.forEach((header, i) => {
      this.doc.text(header, x, startY);
      x += colWidths[i];
    });

    // Table rows
    this.doc.setFont('helvetica', 'normal');
    let y = startY + 7;

    report.session_performance.forEach((session) => {
      x = 20;
      const row = [
        session.session,
        session.sharpe.toFixed(2),
        `${(session.win_rate * 100).toFixed(1)}%`,
        session.profit_factor.toFixed(2),
        session.num_trades.toString(),
      ];

      row.forEach((cell, i) => {
        this.doc.text(cell, x, y);
        x += colWidths[i];
      });

      y += 6;
    });
  }

  private addParameterStability(report: WalkForwardReport) {
    this.doc.setFontSize(14);
    this.doc.setFont('helvetica', 'bold');
    this.doc.text('Parameter Stability Analysis', 20, 20);

    let y = 30;
    this.doc.setFontSize(9);

    report.parameter_stability.forEach((param) => {
      this.doc.setFont('helvetica', 'bold');
      this.doc.text(param.parameter, 20, y);

      this.doc.setFont('helvetica', 'normal');
      this.doc.text(`Mean: ${param.mean.toFixed(2)}`, 80, y);
      this.doc.text(`Std Dev: ${param.std_dev.toFixed(2)}`, 120, y);
      this.doc.text(`CV: ${param.coefficient_of_variation.toFixed(2)}`, 160, y);

      // Stability indicator
      if (param.is_stable) {
        this.doc.setTextColor(0, 128, 0);
        this.doc.text('✓ Stable', 185, y);
      } else {
        this.doc.setTextColor(255, 0, 0);
        this.doc.text('✗ Unstable', 185, y);
      }
      this.doc.setTextColor(0, 0, 0);

      y += 8;
    });
  }

  private addWindows(report: WalkForwardReport) {
    this.doc.setFontSize(14);
    this.doc.setFont('helvetica', 'bold');
    this.doc.text('Walk-Forward Windows', 20, 20);

    let y = 30;
    this.doc.setFontSize(8);

    const windows = report.windows.slice(0, 10); // First 10 windows

    windows.forEach((window, index) => {
      this.doc.setFont('helvetica', 'bold');
      this.doc.text(`Window ${window.window_id}`, 20, y);

      this.doc.setFont('helvetica', 'normal');
      this.doc.text(`IS Sharpe: ${window.in_sample_sharpe.toFixed(2)}`, 50, y);
      this.doc.text(`OOS Sharpe: ${window.out_of_sample_sharpe.toFixed(2)}`, 90, y);
      this.doc.text(`Drawdown: ${(window.max_drawdown * 100).toFixed(1)}%`, 130, y);
      this.doc.text(`Trades: ${window.num_trades}`, 170, y);

      y += 6;

      // Add new page if needed
      if (y > 270 && index < windows.length - 1) {
        this.doc.addPage();
        y = 20;
      }
    });
  }

  private addFooters() {
    const pageCount = this.doc.getNumberOfPages();

    for (let i = 1; i <= pageCount; i++) {
      this.doc.setPage(i);
      this.doc.setFontSize(8);
      this.doc.setTextColor(128, 128, 128);
      this.doc.text(
        `Page ${i} of ${pageCount}`,
        this.doc.internal.pageSize.width / 2,
        this.doc.internal.pageSize.height - 10,
        { align: 'center' }
      );
      this.doc.text(
        'Generated with Claude Code Trading System',
        this.doc.internal.pageSize.width - 20,
        this.doc.internal.pageSize.height - 10,
        { align: 'right' }
      );
      this.doc.setTextColor(0, 0, 0);
    }
  }
}

/**
 * Convenience function to export walk-forward report
 */
export async function exportWalkForwardReportToPDF(
  report: WalkForwardReport,
  options?: PDFExportOptions
): Promise<void> {
  const exporter = new ValidationReportPDFExporter(options?.format);
  await exporter.exportWalkForwardReport(report, options);
}
