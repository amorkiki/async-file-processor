import { useState } from "react"
import { toast } from 'sonner';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { TaskType } from "@/api/types"

interface TaskFormProps {
  onSubmit: (data: { type: TaskType, params: { file_path: string } }) => void;
  loading: boolean;
}

function TaskForm({ onSubmit, loading }: TaskFormProps) {
  const [filePath, setFilePath] = useState('');
  const [type, setType] = useState<TaskType>('download');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!filePath.trim()) {
      toast.error('请输入文件路径');
      return;
    }
    onSubmit({
      type,
      params: { file_path: filePath.trim() }
    })
    // 提交后不清空表单，以免用户误以为失败，但可以清空路径
    setFilePath('');
  }


  return (
    <Card>
      <CardHeader className="text-center">
        <CardTitle>新建任务</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          <div className="space-y-2">
            <Label>文件路径</Label>
            <Input
              id="filePath"
              placeholder="文件路径请输入..."
              value={filePath}
              onChange={e => setFilePath(e.target.value)}
              disabled={loading}
            />
          </div>
          <div className="space-y-2">
            <Label>处理规则</Label>
            <Select
              value={type}
              onValueChange={val => setType(val as TaskType)}
              disabled={loading}
            >
              <SelectTrigger id="taskType"><SelectValue placeholder="选择" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="download">DownLoad</SelectItem>
                <SelectItem value="process">Process</SelectItem>
              </SelectContent>
            </Select>
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





