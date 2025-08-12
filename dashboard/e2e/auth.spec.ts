import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('displays login form when not authenticated', async ({ page }) => {
    // Should show login form since user is not authenticated
    await expect(page.getByText('Sign In')).toBeVisible()
    await expect(page.getByLabel('Email Address')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible()
  })

  test('shows validation for required fields', async ({ page }) => {
    // Try to submit empty form
    await page.getByRole('button', { name: 'Sign In' }).click()
    
    // Check that required field validation works
    const emailInput = page.getByLabel('Email Address')
    const passwordInput = page.getByLabel('Password')
    
    await expect(emailInput).toHaveAttribute('required')
    await expect(passwordInput).toHaveAttribute('required')
  })

  test('allows entering login credentials', async ({ page }) => {
    // Fill in login form
    await page.getByLabel('Email Address').fill('test@example.com')
    await page.getByLabel('Password').fill('password123')
    
    // Verify values are entered
    await expect(page.getByLabel('Email Address')).toHaveValue('test@example.com')
    await expect(page.getByLabel('Password')).toHaveValue('password123')
  })

  test('shows error message for invalid credentials', async ({ page }) => {
    // Mock the API response for failed login
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          requires_2fa: false,
          error: 'Invalid credentials'
        })
      })
    })

    // Fill in and submit form
    await page.getByLabel('Email Address').fill('test@example.com')
    await page.getByLabel('Password').fill('wrongpassword')
    await page.getByRole('button', { name: 'Sign In' }).click()

    // Should show error message
    await expect(page.getByText('Invalid credentials')).toBeVisible()
  })

  test('shows 2FA form when 2FA is required', async ({ page }) => {
    // Mock the API response for 2FA requirement
    await page.route('**/api/auth/login', async route => {
      const request = await route.request()
      const body = await request.postData()
      const data = JSON.parse(body || '{}')
      
      if (data.two_factor_token) {
        // If 2FA token provided, simulate successful login
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            requires_2fa: false,
            tokens: {
              access_token: 'fake-access-token',
              refresh_token: 'fake-refresh-token',
              expires_in: 3600
            },
            user: {
              id: '1',
              email: 'test@example.com',
              name: 'Test User',
              role: 'trader',
              two_factor_enabled: true,
              created_at: '2023-01-01T00:00:00Z',
              last_login: '2023-01-01T00:00:00Z'
            }
          })
        })
      } else {
        // First login attempt - require 2FA
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            requires_2fa: true
          })
        })
      }
    })

    // Fill in and submit initial login form
    await page.getByLabel('Email Address').fill('test@example.com')
    await page.getByLabel('Password').fill('password123')
    await page.getByRole('button', { name: 'Sign In' }).click()

    // Should show 2FA form
    await expect(page.getByLabel('Two-Factor Authentication Code')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Verify Code' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Back to Login' })).toBeVisible()
  })

  test('allows going back from 2FA to login form', async ({ page }) => {
    // Mock 2FA requirement
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          requires_2fa: true
        })
      })
    })

    // Trigger 2FA form
    await page.getByLabel('Email Address').fill('test@example.com')
    await page.getByLabel('Password').fill('password123')
    await page.getByRole('button', { name: 'Sign In' }).click()

    // Verify 2FA form is shown
    await expect(page.getByLabel('Two-Factor Authentication Code')).toBeVisible()

    // Go back to login
    await page.getByRole('button', { name: 'Back to Login' }).click()

    // Should be back to login form
    await expect(page.getByLabel('Email Address')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()
    await expect(page.queryByLabel('Two-Factor Authentication Code')).not.toBeVisible()
  })

  test('successfully authenticates with valid credentials and 2FA', async ({ page }) => {
    let loginAttempts = 0

    // Mock the authentication flow
    await page.route('**/api/auth/login', async route => {
      loginAttempts++
      const request = await route.request()
      const body = await request.postData()
      const data = JSON.parse(body || '{}')
      
      if (loginAttempts === 1) {
        // First attempt - require 2FA
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            requires_2fa: true
          })
        })
      } else if (data.two_factor_token === '123456') {
        // Second attempt with correct 2FA - success
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            requires_2fa: false,
            tokens: {
              access_token: 'fake-access-token',
              refresh_token: 'fake-refresh-token',
              expires_in: 3600
            },
            user: {
              id: '1',
              email: 'test@example.com',
              name: 'Test User',
              role: 'trader',
              two_factor_enabled: true,
              created_at: '2023-01-01T00:00:00Z',
              last_login: '2023-01-01T00:00:00Z'
            }
          })
        })
      }
    })

    // Mock the /me endpoint for user verification
    await page.route('**/api/auth/me', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: '1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'trader',
          two_factor_enabled: true,
          created_at: '2023-01-01T00:00:00Z',
          last_login: '2023-01-01T00:00:00Z'
        })
      })
    })

    // Complete login flow
    await page.getByLabel('Email Address').fill('test@example.com')
    await page.getByLabel('Password').fill('password123')
    await page.getByRole('button', { name: 'Sign In' }).click()

    // Enter 2FA code
    await expect(page.getByLabel('Two-Factor Authentication Code')).toBeVisible()
    await page.getByLabel('Two-Factor Authentication Code').fill('123456')
    await page.getByRole('button', { name: 'Verify Code' }).click()

    // Should redirect to dashboard
    await expect(page.getByText('Dashboard Overview')).toBeVisible()
    await expect(page.getByText('Test User')).toBeVisible() // User name in header
  })
})