import '@testing-library/jest-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TaskForm from '../TaskForm'
import { TooltipProvider } from '@/components/ui/tooltip'
import client from '@/api/client'

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

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

describe('TaskForm', () => {
  const mockOnSubmit = vi.fn();
  const user = userEvent.setup();
  const mockDownloadFilePath = '/tmp/downloaded.txt';
  const mockUploadFilePath = '/tmp/uploaded.txt'
  const downloadInput = '请输入下载链接 (URL)，例如 https://example.com/file.zip'

  beforeEach(() => {
    vi.clearAllMocks();
  })

  it('should render download form on default', () => {
    // act
    render(<TaskForm onSubmit={mockOnSubmit} loading={false} />);

    // expect
    expect(screen.getByText('下载链接 (URL)')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(downloadInput)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '提交任务' })).toBeInTheDocument();
  })

  it('should render process form when changing to Process radio', async () => {
    // background
    render(<TaskForm onSubmit={mockOnSubmit} loading={false} />);

    // act
    await user.click(screen.getByLabelText('Process'));

    // expect
    expect(screen.getByText('未选择文件')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '提交任务' })).toBeInTheDocument();
  })

  it('should render download form when changing to Download radio', async () => {
    // background
    render(<TaskForm onSubmit={mockOnSubmit} loading={false} />);
    const processRadio = screen.getByLabelText('Process');
    const downloadRadio = screen.getByLabelText('Download');
    await user.click(processRadio);
    expect(screen.getByText('未选择文件')).toBeInTheDocument();

    // act
    await user.click(downloadRadio);

    // expect
    expect(screen.getByPlaceholderText(downloadInput)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '提交任务' })).toBeInTheDocument();
  })

  it('should submit download task', async () => {
    // background
    render(<TaskForm onSubmit={mockOnSubmit} loading={false} />);
    (client.post as any).mockResolvedValue({ data: { url: mockDownloadFilePath } });

    // act
    await user.type(screen.getByPlaceholderText(downloadInput), mockDownloadFilePath);
    await user.click(screen.getByRole('button', { name: '提交任务' }));

    // expect
    expect(mockOnSubmit).toHaveBeenCalledWith({
      type: 'download',
      params: { url: mockDownloadFilePath },
    })
  });

  describe('When upload file succeed', () => {
    beforeEach(async () => {
      // background
      (client.post as any).mockResolvedValue({ data: { file_path: mockUploadFilePath } });
      render(
        <TooltipProvider>
          <TaskForm onSubmit={mockOnSubmit} loading={false} />
        </TooltipProvider>
      );
      await user.click(screen.getByLabelText('Process'));

      // act
      const file = new File(['hello'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByLabelText('文件');
      await user.upload(input, file);
    });

    it('should display file_name , Ready status and clear button', async () => {
      await waitFor(() => {
        expect(screen.getByText('test.txt')).toBeInTheDocument()
        expect(screen.getByText('Ready')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'clear-file' })).toBeInTheDocument()
      });
      expect(client.post).toHaveBeenCalledWith(
        '/tasks/upload',
        expect.any(FormData),
        expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } })
      )
    });

    it('should clear uploaded file when clicking clear button', async () => {
      // act
      await user.click(screen.getByRole('button', { name: 'clear-file' }));

      // expect
      expect(screen.queryByText('test.txt')).not.toBeInTheDocument();
      expect(screen.getByText('未选择文件')).toBeInTheDocument();
    })

    it('should submit process file when clicking submit button', async () => {
      // act
      await user.click(screen.getByRole('button', { name: '提交任务' }))

      // expect
      expect(mockOnSubmit).toHaveBeenCalledWith({
        type: 'process',
        params: { file_path: mockUploadFilePath, source_name: 'test.txt' },
      })
    })
  })
})