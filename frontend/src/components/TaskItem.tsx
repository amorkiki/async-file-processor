import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import CancelTaskButton from "@/components/CancelTaskButton"
import type { TaskOut } from "@/api/types"

interface TaskItemProps {
  task: TaskOut
  onCancel: () => void
}

const statusConfig = {
  pending: { label: '等待中', variant: 'ghost' },
  running: { label: '运行中', variant: 'outline' },
  done: { label: '已完成', variant: 'default' },
  failed: { label: '失败', variant: 'destructive' },
  cancelled: { label: '已取消', variant: 'secondary' },
};

function TaskItem({ task, onCancel }: TaskItemProps) {
  const { id, type, status, progress, message, created_at } = task;
  const config = statusConfig[status] || statusConfig.pending;
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
          <Badge variant={config.variant as any}>{config.label}</Badge>
        </div>
        <span className="text-xs text-muted-foreground">
          {new Date(created_at).toLocaleDateString()}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Progress value={progress} className="flex-1 h-1" />
        <span className="text-sm font-mono">{progress}%</span>
      </div>
      {message && <p className="text-xs text-muted-foreground truncate">{message}</p>}
      <div className="flex justify-end">
        {isActive && (
          <CancelTaskButton taskId={task.id} onCancel={onCancel} size="sm" variant="destructive" />
        )}
      </div>
    </div>
  )
}

export default TaskItem
