import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import * as tasksApi from '@/api/tasks'

vi.mock('@/api/tasks', () => ({
  fetchTasks: vi.fn(),
  createTask: vi.fn(),
  cancelTask: vi.fn(),
}))

vi.mock('@/components/TaskForm', () => ({
  default: ({ onSubmit, loading }: any) => (
    <button
      data-testid="mock-submit-btn"
      onClick={() => onSubmit({ type: 'process', params: { file_path: '/tmp/a.txt', source_name: 'test.txt' } })}
      disabled={loading}
    >
      Submit
    </button>
  ),
}))

vi.mock('@/components/ProgressCaed', () => ({
  default: ({ activeTask }: any) => (
    <div data-testid="mock-progress">{activeTask ? activeTask.progress : 'No active'}</div>
  ),
}))

vi.mock('@/components/TaskList', () => ({
  default: ({ tasks }: any) => (
    <div data-testid="mock-task-list">{tasks.length} tasks</div>
  ),
}))

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  })

  it('should fetch TaskList on mount', async () => {
    // act
    (tasksApi.fetchTasks as any).mockResolvedValue({ items: [{ id: '1', status: 'done' }] });
    render(<App />);

    // expect
    await waitFor(() => {
      expect(tasksApi.fetchTasks).toHaveBeenCalled();
    })
    expect(screen.getByTestId('mock-task-list')).toHaveTextContent('1 tasks');
  })

  it('should poll every 2 m', async () => {
    // background
    vi.useFakeTimers();
    (tasksApi.fetchTasks as any).mockResolvedValue({ items: [] });

    // act 
    render(<App />);

    // expect
    expect(tasksApi.fetchTasks).toHaveBeenCalledTimes(1);

    // act
    vi.advanceTimersByTime(2000);

    // expect
    expect(tasksApi.fetchTasks).toHaveBeenCalledTimes(2);

    // act
    vi.advanceTimersByTime(2000);

    // expect
    expect(tasksApi.fetchTasks).toHaveBeenCalledTimes(3);
    vi.useRealTimers();
  })

  it('should refresh TaskList when new task submit', async () => {
    // background
    const user = userEvent.setup();
    const mockCreate = tasksApi.createTask as any;
    const mockFetch = tasksApi.fetchTasks as any;
    mockCreate.mockResolvedValue({ task_id: 'new-123' });
    mockFetch.mockResolvedValue({ items: [{ id: 'new-123', status: 'pending' }] });
    render(<App />);
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());

    // act
    await user.click(screen.getByTestId('mock-submit-btn'));

    // expect
    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalled();
      expect(mockFetch).toHaveBeenCalledTimes(2);
    })
  })
})