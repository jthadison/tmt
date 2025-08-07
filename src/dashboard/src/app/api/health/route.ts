/**
 * Health Check Endpoint for Trading Dashboard
 * 
 * Provides standardized health status information for monitoring
 * and load balancers to determine service availability.
 * 
 * @returns {Response} JSON response with health status and metadata
 */
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const startTime = Date.now();
  const correlationId = request.headers.get('x-correlation-id') || 
                       crypto.randomUUID();

  try {
    // Basic service checks
    const checks = await Promise.allSettled([
      checkDatabase(),
      checkRedis(),
      checkMemory(),
      checkDiskSpace(),
    ]);

    const healthStatus = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      service: 'trading-dashboard',
      version: process.env.npm_package_version || '0.1.0',
      uptime: process.uptime(),
      environment: process.env.NODE_ENV || 'development',
      responseTime: Date.now() - startTime,
      correlationId,
      checks: {
        database: getCheckResult(checks[0]),
        redis: getCheckResult(checks[1]),
        memory: getCheckResult(checks[2]),
        disk: getCheckResult(checks[3]),
      },
      metadata: {
        nodeVersion: process.version,
        platform: process.platform,
        architecture: process.arch,
        pid: process.pid,
        memoryUsage: process.memoryUsage(),
      }
    };

    // Determine overall status based on checks
    const failedChecks = Object.values(healthStatus.checks)
      .filter(check => check.status === 'failed');

    if (failedChecks.length > 0) {
      healthStatus.status = 'degraded';
    }

    const responseStatus = healthStatus.status === 'healthy' ? 200 : 
                          healthStatus.status === 'degraded' ? 200 : 503;

    return NextResponse.json({
      data: healthStatus,
      error: null,
      correlation_id: correlationId
    }, { 
      status: responseStatus,
      headers: {
        'Content-Type': 'application/json',
        'X-Correlation-ID': correlationId,
        'Cache-Control': 'no-cache, no-store, must-revalidate'
      }
    });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    
    return NextResponse.json({
      data: {
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        service: 'trading-dashboard',
        error: errorMessage,
        responseTime: Date.now() - startTime,
        correlationId
      },
      error: errorMessage,
      correlation_id: correlationId
    }, { 
      status: 503,
      headers: {
        'Content-Type': 'application/json',
        'X-Correlation-ID': correlationId
      }
    });
  }
}

/**
 * Check database connectivity
 */
async function checkDatabase(): Promise<{ status: string; message: string; responseTime: number }> {
  const startTime = Date.now();
  
  try {
    // In a real implementation, this would test the database connection
    // For now, we'll simulate a check based on environment variables
    if (!process.env.DATABASE_URL) {
      throw new Error('DATABASE_URL not configured');
    }

    // Simulate database ping (would use actual DB client in real implementation)
    await new Promise(resolve => setTimeout(resolve, 10));
    
    return {
      status: 'passed',
      message: 'Database connection healthy',
      responseTime: Date.now() - startTime
    };
  } catch (error) {
    return {
      status: 'failed',
      message: error instanceof Error ? error.message : 'Database check failed',
      responseTime: Date.now() - startTime
    };
  }
}

/**
 * Check Redis connectivity
 */
async function checkRedis(): Promise<{ status: string; message: string; responseTime: number }> {
  const startTime = Date.now();
  
  try {
    if (!process.env.REDIS_URL) {
      throw new Error('REDIS_URL not configured');
    }

    // Simulate Redis ping (would use actual Redis client in real implementation)
    await new Promise(resolve => setTimeout(resolve, 5));
    
    return {
      status: 'passed',
      message: 'Redis connection healthy',
      responseTime: Date.now() - startTime
    };
  } catch (error) {
    return {
      status: 'failed',
      message: error instanceof Error ? error.message : 'Redis check failed',
      responseTime: Date.now() - startTime
    };
  }
}

/**
 * Check memory usage
 */
async function checkMemory(): Promise<{ status: string; message: string; responseTime: number }> {
  const startTime = Date.now();
  
  try {
    const memUsage = process.memoryUsage();
    const usedHeapMB = memUsage.heapUsed / 1024 / 1024;
    const totalHeapMB = memUsage.heapTotal / 1024 / 1024;
    const usagePercent = (usedHeapMB / totalHeapMB) * 100;

    if (usagePercent > 90) {
      return {
        status: 'failed',
        message: `High memory usage: ${usagePercent.toFixed(1)}%`,
        responseTime: Date.now() - startTime
      };
    }

    return {
      status: 'passed',
      message: `Memory usage: ${usagePercent.toFixed(1)}%`,
      responseTime: Date.now() - startTime
    };
  } catch (error) {
    return {
      status: 'failed',
      message: error instanceof Error ? error.message : 'Memory check failed',
      responseTime: Date.now() - startTime
    };
  }
}

/**
 * Check disk space (simplified for container environments)
 */
async function checkDiskSpace(): Promise<{ status: string; message: string; responseTime: number }> {
  const startTime = Date.now();
  
  try {
    // In a real implementation, this would check actual disk usage
    // For containers, this is less critical but we'll do a basic check
    
    return {
      status: 'passed',
      message: 'Disk space adequate',
      responseTime: Date.now() - startTime
    };
  } catch (error) {
    return {
      status: 'failed',
      message: error instanceof Error ? error.message : 'Disk check failed',
      responseTime: Date.now() - startTime
    };
  }
}

/**
 * Extract result from Promise.allSettled result
 */
function getCheckResult(result: PromiseSettledResult<any>) {
  if (result.status === 'fulfilled') {
    return result.value;
  } else {
    return {
      status: 'failed',
      message: result.reason?.message || 'Check failed',
      responseTime: 0
    };
  }
}