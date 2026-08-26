import { useState } from "react"
import { toast } from 'sonner';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import type { TaskType } from "@/api/types"

interface TaskFormProps {
  onSubmit: (data: { type: TaskType; params: { url?: string; file_path?: string } }) => void;
  loading: boolean;
}

function TaskForm({ onSubmit, loading }: TaskFormProps) {
  const [filePath, setFilePath] = useState('');
  const [type, setType] = useState<TaskType>('download');

  const handleTypeChange = (val: string) => {
    setType(val as TaskType);
    setFilePath('')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!filePath.trim()) {
      toast.error(type === 'download' ? '请输入下载链接' : '请输入文件路径');
      return;
    }
    const params = type === 'download'
      ? { url: filePath.trim() }
      : { file_path: filePath.trim() };

    onSubmit({
      type,
      params: params
    })
    // 提交后不清空表单，以免用户误以为失败，但可以清空路径
    setFilePath('');
  }

  const isDownload = type === 'download';
  const inputLabel = isDownload ? '下载链接 (URL)' : '本地文件路径';
  const inputPlaceholder = isDownload
    ? '请输入下载链接 (URL)，例如 https://example.com/file.zip'
    : '请输入本地文件路径，例如 /tmp/test.txt';

  return (
    <Card className="h-[500px] flex flex-col">
      <CardHeader className="text-center">
        <CardTitle>新建任务</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col p-8">
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

            <div className="space-y-2">
              <Label>{inputLabel}</Label>
              <Input
                id="filePath"
                placeholder={inputPlaceholder}
                value={filePath}
                onChange={e => setFilePath(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? '提交中...' : '提交任务'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}

export default TaskForm





