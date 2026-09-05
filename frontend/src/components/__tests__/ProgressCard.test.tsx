import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ProgressCard from '../ProgressCard'
import type { TaskOut } from '@/api/types'

vi.mock('@/components/CancelTaskButton', () => ({
  default: ({ taskId, onCancel }: any) => (
    <button data-testid="mock-cancel-btn" onClick={onCancel}>
      Mock Cancel {taskId}
    </button>
  ),
}));

describe('ProgressCard', () => {
  const mockOnCancel = vi.fn();

  it('should display progress and cancel button when has active task', () => {
    // background
    const activeTask: TaskOut = {
      id: '123',
      type: 'process',
      source_name: 'a.txt',
      status: 'running',
      progress: 75,
      message: '处理中...',
      created_at: '2026-09-04T00:00:00Z',
    };

    // act
    render(<ProgressCard activeTask={activeTask} onCancel={mockOnCancel} />);

    // expect
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('处理中...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mock Cancel 123' })).toBeInTheDocument();
  })

  it('should not display progress and cancel button when has no active task', () => {
    render(<ProgressCard activeTask={null as any} onCancel={mockOnCancel} />);
    expect(screen.getByText('暂无进行中的任务')).toBeInTheDocument();
  })
})