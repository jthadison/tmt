import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ThemeToggle from '@/components/ui/ThemeToggle'
import { ThemeProvider } from '@/context/ThemeContext'

// Mock the ThemeContext
const mockToggleTheme = jest.fn()
jest.mock('@/context/ThemeContext', () => ({
  ...jest.requireActual('@/context/ThemeContext'),
  useTheme: () => ({
    theme: 'dark',
    toggleTheme: mockToggleTheme
  })
}))

describe('ThemeToggle Component', () => {
  beforeEach(() => {
    mockToggleTheme.mockClear()
  })

  it('renders theme toggle button', () => {
    render(<ThemeToggle />)
    
    const button = screen.getByRole('button')
    expect(button).toBeInTheDocument()
    expect(button).toHaveAttribute('aria-label', 'Switch to light mode')
  })

  it('calls toggleTheme when clicked', async () => {
    const user = userEvent.setup()
    render(<ThemeToggle />)
    
    const button = screen.getByRole('button')
    await user.click(button)
    
    expect(mockToggleTheme).toHaveBeenCalledTimes(1)
  })

  it('displays sun icon for dark theme', () => {
    render(<ThemeToggle />)
    
    const sunIcon = screen.getByRole('button').querySelector('svg')
    expect(sunIcon).toBeInTheDocument()
    expect(sunIcon).toHaveClass('text-yellow-500')
  })

  it('has proper styling classes', () => {
    render(<ThemeToggle />)
    
    const button = screen.getByRole('button')
    expect(button).toHaveClass('p-2', 'rounded-lg', 'transition-colors')
  })
})

// Test with light theme separately  
describe('ThemeToggle Component - Light Theme', () => {
  const mockToggleThemeLight = jest.fn()
  
  beforeEach(() => {
    // Create a new mock for light theme
    require('@/context/ThemeContext').useTheme = jest.fn(() => ({
      theme: 'light', 
      toggleTheme: mockToggleThemeLight
    }))
    mockToggleThemeLight.mockClear()
  })

  it('displays correct aria-label for light theme', () => {
    render(<ThemeToggle />)
    
    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-label', 'Switch to dark mode')
  })

  it('displays moon icon for light theme', () => {
    render(<ThemeToggle />)
    
    const moonIcon = screen.getByRole('button').querySelector('svg')
    expect(moonIcon).toBeInTheDocument()
    expect(moonIcon).toHaveClass('text-blue-400')
  })
})