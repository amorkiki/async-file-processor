import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CancelTaskButton from '../CancelTaskButton'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/api/tasks', () => ({
  cancelTask: vi.fn(() => Promise.resolve()),
}))

describe('CancelTaskButton', () => {
  const mockOnCancel = vi.fn();
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
  })

  it('should open dialog when ', async () => {
    // background
    render(<CancelTaskButton taskId="123" onCancel={mockOnCancel} />);

    // act
    await user.click(screen.getByRole('button', { name: '取消任务' }));

    // expect
    expect(screen.getByText('确认取消任务？')).toBeInTheDocument();
    expect(screen.getByText('继续执行')).toBeInTheDocument();
    expect(screen.getByText('确认取消')).toBeInTheDocument();
  })

  it('should cancel task when clicking “确认取消” button', async () => {
    // background
    const { cancelTask } = await import('@/api/tasks');
    render(<CancelTaskButton taskId="456" onCancel={mockOnCancel} />);
    await user.click(screen.getByRole('button', { name: '取消任务' }));

    // act
    user.click(screen.getByRole('button', { name: '确认取消' }));

    // expect
    await waitFor(() => {
      expect(cancelTask).toHaveBeenCalledWith('456');
      expect(mockOnCancel).toHaveBeenCalled();
    })
  })

  it('should not cancel task when clicking “继续执行” button', async () => {
    // background
    const { cancelTask } = await import('@/api/tasks');
    render(<CancelTaskButton taskId="456" onCancel={mockOnCancel} />);
    await user.click(screen.getByRole('button', { name: '取消任务' }));

    // act
    user.click(screen.getByRole('button', { name: '继续执行' }));

    // expect
    expect(cancelTask).not.toHaveBeenCalled();
    expect(mockOnCancel).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.queryByText('确认取消任务？')).not.toBeInTheDocument();
    })
  })
})