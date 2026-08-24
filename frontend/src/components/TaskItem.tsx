import { CheckCircle2, XCircle, Loader2, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import type { TaskOut } from "@/api/types"

interface TaskItemProps {
  task: TaskOut
  onCancel: () => void
}

const statusConfig = {
  pending: { label: '等待中', color: 'bg-yellow-500', icon: Clock },
  running: { label: '运行中', color: 'bg-blue-500', icon: Loader2 },
  done: { label: '已完成', color: 'bg-green-500', icon: CheckCircle2 },
  failed: { label: '失败', color: 'bg-red-500', icon: XCircle },
  cancelled: { label: '已取消', color: 'bg-gray-500', icon: XCircle },
};

function TaskItem({ task, onCancel }: TaskItemProps) {
  const { id, type, status, progress, message, created_at } = task;
  const config = statusConfig[status] || statusConfig.pending;
  const Icon = config.icon;
  const isActive = status === 'pending' || status === 'running';

  const handleCancel = async () => {
    if (window.confirm('确认取消该任务？')) {
      try {
        // 导入 cancelTask
        const { cancelTask } = await import('@/api/tasks');
        await cancelTask(id);
        onCancel(); // 刷新列表
      } catch (err: any) {
        toast.error(err.message || '取消失败');
      }
    }
  }

  return (
    <div className="border rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge variant="outline">{type}</Badge>
          <Badge className={config.color}>{config.label}</Badge>
        </div>
        <span className="text-xs text-muted-foreground">
          {new Date(created_at).toLocaleDateString()}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Progress value={progress} className="flex-1 h-2" />
        <span className="text-sm font-mono">{progress}%</span>
      </div>
      {message && <p className="text-xs text-muted-foreground truncate">{message}</p>}
      <div className="flex justify-end">
        {isActive && (
          <Button
            variant="destructive"
            size="sm"
            onClick={handleCancel}
          >
            取消任务
          </Button>
        )}
      </div>
    </div>
  )
}

export default TaskItem
