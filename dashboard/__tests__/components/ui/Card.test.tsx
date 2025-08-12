import { render, screen } from '@testing-library/react'
import Card from '@/components/ui/Card'

describe('Card Component', () => {
  it('renders children content correctly', () => {
    render(
      <Card>
        <p>Test content</p>
      </Card>
    )
    
    expect(screen.getByText('Test content')).toBeInTheDocument()
  })

  it('renders with title when provided', () => {
    render(
      <Card title="Test Title">
        <p>Test content</p>
      </Card>
    )
    
    expect(screen.getByText('Test Title')).toBeInTheDocument()
    expect(screen.getByText('Test content')).toBeInTheDocument()
  })

  it('renders without title when not provided', () => {
    render(
      <Card>
        <p>Test content</p>
      </Card>
    )
    
    expect(screen.queryByRole('heading')).not.toBeInTheDocument()
    expect(screen.getByText('Test content')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <Card className="custom-class">
        <p>Test content</p>
      </Card>
    )
    
    expect(container.firstChild).toHaveClass('custom-class')
  })

  it('has proper styling classes', () => {
    const { container } = render(
      <Card title="Test">
        <p>Content</p>
      </Card>
    )
    
    const cardElement = container.firstChild as HTMLElement
    expect(cardElement).toHaveClass('bg-white', 'dark:bg-gray-900', 'border', 'rounded-lg', 'p-6')
  })

  it('renders title with correct heading styles', () => {
    render(
      <Card title="Test Title">
        <p>Content</p>
      </Card>
    )
    
    const titleElement = screen.getByText('Test Title')
    expect(titleElement).toHaveClass('text-lg', 'font-semibold', 'text-gray-900', 'dark:text-white', 'mb-4')
  })
})