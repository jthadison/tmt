import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeProvider, useTheme } from '@/context/ThemeContext'

// Test component to access theme context
function TestComponent() {
  const { theme, toggleTheme } = useTheme()
  
  return (
    <div>
      <span data-testid="current-theme">{theme}</span>
      <button onClick={toggleTheme} data-testid="toggle-button">
        Toggle Theme
      </button>
    </div>
  )
}

describe('ThemeContext', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    jest.clearAllMocks()
    
    // Mock document.documentElement
    Object.defineProperty(document, 'documentElement', {
      value: {
        classList: {
          remove: jest.fn(),
          add: jest.fn()
        }
      },
      writable: true
    })
  })

  it('provides default dark theme', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )

    expect(screen.getByTestId('current-theme')).toHaveTextContent('dark')
  })

  it('toggles between light and dark themes', async () => {
    const user = userEvent.setup()
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )

    const themeDisplay = screen.getByTestId('current-theme')
    const toggleButton = screen.getByTestId('toggle-button')

    // Initially dark
    expect(themeDisplay).toHaveTextContent('dark')

    // Toggle to light
    await user.click(toggleButton)
    expect(themeDisplay).toHaveTextContent('light')

    // Toggle back to dark
    await user.click(toggleButton)
    expect(themeDisplay).toHaveTextContent('dark')
  })

  it('persists theme preference in localStorage', async () => {
    const user = userEvent.setup()
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )

    const toggleButton = screen.getByTestId('toggle-button')

    // Toggle to light theme
    await user.click(toggleButton)
    
    expect(localStorage.setItem).toHaveBeenCalledWith('theme', 'light')
  })

  it('loads saved theme from localStorage', () => {
    // Mock localStorage to return saved light theme
    localStorage.getItem.mockReturnValue('light')
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )

    expect(screen.getByTestId('current-theme')).toHaveTextContent('light')
  })

  it('applies theme classes to document root', async () => {
    const user = userEvent.setup()
    const mockClassList = {
      remove: jest.fn(),
      add: jest.fn()
    }
    
    Object.defineProperty(document, 'documentElement', {
      value: { classList: mockClassList },
      writable: true
    })

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )

    const toggleButton = screen.getByTestId('toggle-button')

    // Toggle to light theme
    await user.click(toggleButton)

    expect(mockClassList.remove).toHaveBeenCalledWith('light', 'dark')
    expect(mockClassList.add).toHaveBeenCalledWith('light')
  })

  it('throws error when useTheme is used outside ThemeProvider', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation()

    expect(() => {
      render(<TestComponent />)
    }).toThrow('useTheme must be used within a ThemeProvider')

    consoleSpy.mockRestore()
  })

  it('sets dark theme as default when no saved preference', () => {
    localStorage.getItem.mockReturnValue(null)
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )

    expect(screen.getByTestId('current-theme')).toHaveTextContent('dark')
    expect(localStorage.setItem).toHaveBeenCalledWith('theme', 'dark')
  })
})