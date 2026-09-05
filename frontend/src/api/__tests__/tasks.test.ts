import { describe, it, expect, vi, beforeEach } from 'vitest'
import client from '@/api/client'
import { createTask, fetchTasks, fetchTaskById, cancelTask } from '@/api/tasks'

// 模拟 client
vi.mock('@/api/client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    }
  }
}))

describe('API: tasks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  })

  it('should call POST /tasks/ when createTask', async () => {
    // background
    const mockData = { type: 'process', params: { file_path: '/tmp/a.txt' } };
    const mockResponse = { data: { task_id: '123' } };
    (client.post as any).mockResolvedValue(mockResponse)

    // act
    const result = await createTask(mockData as any);

    // expect
    expect(client.post).toHaveBeenCalledWith('/tasks/', mockData);
    expect(result).toEqual(mockResponse.data);
  })

  it('should call GET /tasks/ by params when fetchTasks', async () => {
    // background
    const mockResponse = { data: { items: [], total: 0, page: 1, size: 20, pages: 0 } };
    (client.get as any).mockResolvedValue(mockResponse);

    // act
    const params = { status: 'pending', page: 2 };
    const result = await fetchTasks(params as any);

    // expect
    expect(client.get).toHaveBeenCalledWith('/tasks/', { params: params });
    expect(result).toEqual(mockResponse.data);
  })

  it('should call GET /tasks/ by task_id when fetchTaskById', async () => {
    // background
    const mockResponse = {
      data: {
        items: [{
          id: '123',
          type: 'process',
          source_name: 'test.txt',
          status: 'pending',
          progress: 50,
          message: 'Processing...',
          created_at: '2026-09-04T00:00:00Z',
        }], total: 1, page: 1, size: 20, pages: 1
      }
    };
    (client.get as any).mockResolvedValue(mockResponse);

    // act
    const result = await fetchTaskById('123')

    // expect
    expect(client.get).toHaveBeenCalledWith('/tasks/123');
    expect(result).toEqual(mockResponse.data);
  })

  it('should call DELETE /tasks/{id} when cancelTask', async () => {
    // background
    (client.delete as any).mockResolvedValue({});

    // act
    await cancelTask('test-1')

    // expect
    expect(client.delete).toHaveBeenCalledWith('/tasks/test-1')
  })
})