import { useRef, useState } from "react"
import { CircleX, FolderSearch, File, CircleCheckBig, Loader } from "lucide-react";
import { toast } from 'sonner';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { TaskType } from "@/api/types"
import client from "@/api/client";

interface TaskFormProps {
  onSubmit: (data: { type: TaskType; params: { url?: string; file_path?: string } }) => void;
  loading: boolean;
}

function TaskForm({ onSubmit, loading }: TaskFormProps) {
  const [filePath, setFilePath] = useState('');
  const [url, setUrl] = useState('')
  const [fileName, setFileName] = useState('');
  const [type, setType] = useState<TaskType>('download');
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isDownload = type === 'download';

  const handleTypeChange = (val: string) => {
    setType(val as TaskType);
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';  // 重置 input，允许重复选择同一个文件
    setFileName(file.name);
    setIsUploading(true);

    const formData = new FormData();
    formData.append('file', file)

    try {
      const response = await client.post('/tasks/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const data = response.data;
      setFilePath(data.file_path);
      toast.success(`"${file.name}" 已提交`);
    } catch (error) {
      const errorMsg = error.message || error.response?.data?.message || '文件上传失败，请重试';
      setFileName('');
      setFilePath('');
      toast.error(errorMsg);
    } finally {
      setIsUploading(false);
    }
  }

  const handleClearFile = () => {
    setFileName('');
    setFilePath('');
    setIsUploading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let params = {}
    if (isDownload && url.trim()) {
      params = { url: url.trim() }
    } else if (!isDownload && filePath.trim()) {
      params = { file_path: filePath.trim(), source_name: fileName };
    } else {
      toast.error(type === 'download' ? '请输入下载链接' : '请输入文件路径');
      return;
    }
    onSubmit({
      type,
      params: params
    })
  }


  return (
    <Card className="h-[500px] flex flex-col">
      <CardHeader className="text-center">
        <CardTitle>新建任务</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col p-6">
        <form onSubmit={handleSubmit} className="flex flex-col flex-1">
          <div className="flex-1 space-y-6">
            <div className="space-y-2">
              <Label>处理规则</Label>
              <RadioGroup
                defaultValue="download"
                onValueChange={handleTypeChange}
                disabled={loading}
                className="flex gap-6 pt-1"
              >
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="download" id="download" className="border-2 data-[state=checked]:border-black data-[state=checked]:bg-black data-[state=checked]:text-white" />
                  <Label htmlFor="download" className="cursor-pointer">Download</Label>
                </div>
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="process" id="process" className="border-2 data-[state=checked]:border-black data-[state=checked]:bg-black data-[state=checked]:text-white" />
                  <Label htmlFor="process" className="cursor-pointer">Process</Label>
                </div>
              </RadioGroup>
            </div>
            {/* download */}
            <div className="space-y-2" hidden={!isDownload}>
              <Label>下载链接 (URL)</Label>
              <Input
                id="filePath"
                placeholder="请输入下载链接 (URL)，例如 https://example.com/file.zip"
                value={url}
                onChange={e => setUrl(e.target.value)}
                disabled={loading}
              />
            </div>
            {/* process */}
            <div className="space-y-2" hidden={isDownload}>
              <Label htmlFor="file-upload">文件</Label>
              <div className="flex items-center gap-2" hidden={isDownload}>
                {fileName ? (
                  <div className="flex-1 flex min-w-0 items-center border rounded-md px-3 py-2 bg-muted/50 gap-2">
                    <Tooltip>
                      <TooltipTrigger className="text-sm truncate flex-1 min-w-0">
                        <span><File size={16} className="inline" /> {fileName}</span>
                      </TooltipTrigger>
                      <TooltipContent><p>{fileName}</p></TooltipContent>
                    </Tooltip>
                    <span className="text-xs text-green-600 ml-2 flex-shrink-0">
                      <CircleCheckBig size={16} className="inline" /> Ready
                    </span>
                    <button
                      type="button"
                      onClick={handleClearFile}
                      aria-label="clear-file"
                      className="text-xs text-muted-foreground hover:text-destructive flex-shrink-0"
                    >
                      <CircleX size={16} />
                    </button>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-between border rounded-md px-3 py-2 text-muted-foreground text-sm">
                    <span>未选择文件</span>
                  </div>
                )}
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleUploadClick}
                  disabled={loading || isUploading}
                  className="flex-shrink-0"
                >
                  {isUploading ? <Loader /> : <FolderSearch />}
                </Button>
                {/* 隐藏的文件选择器 */}
                <input
                  id="file-upload"
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  className="hidden"
                  accept=".pdf,.docx,.doc,.txt,.md,.csv,.json"
                />
              </div>
            </div>

          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {isUploading ? '上传中...' : loading ? '提交中...' : '提交任务'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}

export default TaskForm





