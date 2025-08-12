import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginForm from '@/components/auth/LoginForm'
import { AuthProvider } from '@/context/AuthContext'

// Mock the auth context
const mockLogin = jest.fn()
jest.mock('@/context/AuthContext', () => ({
  ...jest.requireActual('@/context/AuthContext'),
  useAuth: () => ({
    login: mockLogin,
    isLoading: false,
    error: null
  })
}))

const renderLoginForm = () => {
  return render(
    <AuthProvider>
      <LoginForm />
    </AuthProvider>
  )
}

describe('LoginForm Component', () => {
  beforeEach(() => {
    mockLogin.mockClear()
  })

  it('renders login form with email and password fields', () => {
    renderLoginForm()
    
    expect(screen.getByRole('heading', { name: 'Sign In' })).toBeInTheDocument()
    expect(screen.getByLabelText('Email Address')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument()
  })

  it('allows user to enter email and password', async () => {
    const user = userEvent.setup()
    renderLoginForm()
    
    const emailInput = screen.getByLabelText('Email Address')
    const passwordInput = screen.getByLabelText('Password')
    
    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    
    expect(emailInput).toHaveValue('test@example.com')
    expect(passwordInput).toHaveValue('password123')
  })

  it('submits form with correct credentials', async () => {
    const user = userEvent.setup()
    mockLogin.mockResolvedValue({ success: true, requires_2fa: false })
    
    renderLoginForm()
    
    const emailInput = screen.getByLabelText('Email Address')
    const passwordInput = screen.getByLabelText('Password')
    const submitButton = screen.getByRole('button', { name: 'Sign In' })
    
    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)
    
    expect(mockLogin).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password123'
    })
  })

  it('shows 2FA input when 2FA is required', async () => {
    const user = userEvent.setup()
    mockLogin.mockResolvedValue({ success: false, requires_2fa: true })
    
    renderLoginForm()
    
    const emailInput = screen.getByLabelText('Email Address')
    const passwordInput = screen.getByLabelText('Password')
    const submitButton = screen.getByRole('button', { name: 'Sign In' })
    
    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByLabelText('Two-Factor Authentication Code')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Verify Code' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Back to Login' })).toBeInTheDocument()
    })
  })

  it('allows entering 2FA code', async () => {
    const user = userEvent.setup()
    mockLogin.mockResolvedValueOnce({ success: false, requires_2fa: true })
    
    renderLoginForm()
    
    // First, trigger 2FA requirement
    await user.type(screen.getByLabelText('Email Address'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Sign In' }))
    
    await waitFor(() => {
      expect(screen.getByLabelText('Two-Factor Authentication Code')).toBeInTheDocument()
    })
    
    const twoFactorInput = screen.getByLabelText('Two-Factor Authentication Code')
    await user.type(twoFactorInput, '123456')
    
    expect(twoFactorInput).toHaveValue('123456')
  })

  it('goes back to login form when "Back to Login" is clicked', async () => {
    const user = userEvent.setup()
    mockLogin.mockResolvedValueOnce({ success: false, requires_2fa: true })
    
    renderLoginForm()
    
    // First, trigger 2FA requirement
    await user.type(screen.getByLabelText('Email Address'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Sign In' }))
    
    await waitFor(() => {
      expect(screen.getByLabelText('Two-Factor Authentication Code')).toBeInTheDocument()
    })
    
    // Click back to login
    const backButton = screen.getByRole('button', { name: 'Back to Login' })
    await user.click(backButton)
    
    expect(screen.getByLabelText('Email Address')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.queryByLabelText('Two-Factor Authentication Code')).not.toBeInTheDocument()
  })

  it('displays error message when login fails', async () => {
    const user = userEvent.setup()
    mockLogin.mockResolvedValue({ 
      success: false, 
      requires_2fa: false, 
      error: 'Invalid credentials' 
    })
    
    renderLoginForm()
    
    await user.type(screen.getByLabelText('Email Address'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'wrongpassword')
    await user.click(screen.getByRole('button', { name: 'Sign In' }))
    
    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })
  })

  it('validates required fields', async () => {
    const user = userEvent.setup()
    renderLoginForm()
    
    const submitButton = screen.getByRole('button', { name: 'Sign In' })
    await user.click(submitButton)
    
    const emailInput = screen.getByLabelText('Email Address')
    const passwordInput = screen.getByLabelText('Password')
    
    expect(emailInput).toBeRequired()
    expect(passwordInput).toBeRequired()
  })
})