import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import TaskList from '../TaskList'
import type { TaskOut } from '@/api/types'

vi.mock('@/components/TaskItem', () => ({
  default: ({ task }: any) => <div data-testid="task-item">{task.source_name}</div>,
}))

describe('TaskList', () => {
  const mockOnCancel = vi.fn();

  it('should render Task List when has any task', () => {
    // background
    const tasks: TaskOut[] = [
      { id: '1', type: 'process', source_name: 'a.txt', status: 'pending', progress: 0, message: null, created_at: '2026-01-01T00:00:00Z' },
      { id: '2', type: 'process', source_name: 'b.txt', status: 'done', progress: 100, message: null, created_at: '2026-01-02T00:00:00Z' },
    ];

    // act
    render(<TaskList tasks={tasks} onCancel={mockOnCancel} />);

    // expect
    const items = screen.getAllByTestId('task-item');
    expect(items).toHaveLength(2);
    expect(screen.getByText('a.txt')).toBeInTheDocument();
    expect(screen.getByText('b.txt')).toBeInTheDocument();
  })

  it('should not show Task List when has no task', () => {
    // act
    render(<TaskList tasks={[]} onCancel={mockOnCancel} />);

    // expect
    expect(screen.getByText('暂无任务')).toBeInTheDocument();
  })
})

