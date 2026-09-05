import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import TaskItem from '../TaskItem'
import { TooltipProvider } from '@/components/ui/tooltip'
import type { TaskOut } from '@/api/types'

vi.mock('@/components/CancelTaskButton', () => ({
  default: ({ taskId, onCancel }: any) => (
    <button data-testid="mock-cancel-btn" onClick={onCancel}>
      Cancel {taskId}
    </button>
  ),
}));

describe('TaskItem', () => {
  const mockOnCancel = vi.fn()
  const mockTask: TaskOut = {
    id: '123',
    type: 'process',
    source_name: 'test.txt',
    status: 'pending',
    progress: 50,
    message: 'Processing...',
    created_at: '2026-09-04T00:00:00Z',
  }

  it('should display File Name, Type, Status,Create Time', () => {
    // act
    render(<TooltipProvider><TaskItem task={mockTask} onCancel={mockOnCancel} /></TooltipProvider>);

    // expect
    expect(screen.getByText('test.txt')).toBeInTheDocument();
    expect(screen.getByText('process')).toBeInTheDocument();
    expect(screen.getByText('等待中')).toBeInTheDocument();
    expect(screen.getByText('9/4/2026')).toBeInTheDocument();
  })

  it('should display progress', () => {
    // act
    render(<TooltipProvider><TaskItem task={mockTask} onCancel={mockOnCancel} /></TooltipProvider>);

    // expect
    expect(screen.getByText('50%')).toBeInTheDocument();
  })

  it('shoud show cancel button when status is pening or running', () => {
    // act
    const { rerender } = render(<TooltipProvider><TaskItem task={mockTask} onCancel={mockOnCancel} /></TooltipProvider>);
    // expect
    expect(screen.getByTestId('mock-cancel-btn')).toBeInTheDocument();

    // act
    rerender(<TooltipProvider><TaskItem task={{ ...mockTask, status: 'done' }} onCancel={mockOnCancel} /></TooltipProvider>);
    // expect
    expect(screen.queryByTestId('mock-cancel-btn')).not.toBeInTheDocument();

    // act
    rerender(<TooltipProvider><TaskItem task={{ ...mockTask, status: 'running' }} onCancel={mockOnCancel} /></TooltipProvider>);
    // expect
    expect(screen.getByTestId('mock-cancel-btn')).toBeInTheDocument();
  })

  it('should display message when has', () => {
    // act
    const { rerender } = render(<TooltipProvider><TaskItem task={mockTask} onCancel={mockOnCancel} /></TooltipProvider>);

    // expect
    expect(screen.getByText('Processing...')).toBeInTheDocument();

    // act
    rerender(<TooltipProvider><TaskItem task={{ ...mockTask, message: '' }} onCancel={mockOnCancel} /></TooltipProvider>)

    // expect
    expect(screen.queryByText('Processing...')).not.toBeInTheDocument();
  })

})
