import { File } from "lucide-react";
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import CancelTaskButton from "@/components/CancelTaskButton"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
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
  const { id, type, status, progress, message, created_at, source_name } = task;
  const config = statusConfig[status] || statusConfig.pending;
  const isActive = status === 'pending' || status === 'running';

  return (
    <div className="border rounded-lg p-4 space-y-3 hover:bg-muted/30 transition-colors">
      {/* 第一行：文件名 + 类型 + 状态 + 时间 */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Tooltip>
            <TooltipTrigger className="text-sm font-medium truncate min-w-0">
              <span>
                <File size={16} className="inline" /> {source_name || '未命名文件'}
              </span>
            </TooltipTrigger>
            <TooltipContent>
              <p>{source_name || '未命名文件'}</p>
            </TooltipContent>
          </Tooltip>
          <Badge variant="outline" className="text-xs flex-shrink-0">
            {type}
          </Badge>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Badge variant={config.variant as any}>
            {config.label}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {new Date(created_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      {/* 第二行：进度条 + 百分比 */}
      <div className="flex items-center gap-3">
        <Progress
          value={progress}
          className="flex-1 h-1"
        />
        <span className="text-sm font-mono text-muted-foreground w-12 text-right">
          {progress}%
        </span>
      </div>

      {/* 第三行：状态消息（如果有） */}
      {message && (
        <p className="text-xs text-muted-foreground truncate">
          {message}
        </p>

      )}

      {/* 第四行：取消按钮（仅活跃任务） */}
      {isActive && (
        <div className="flex justify-end pt-1 border-t border-border/50">
          <CancelTaskButton
            taskId={id}
            onCancel={onCancel}
            size="sm"
          />
        </div>
      )}
    </div>
  )
}

export default TaskItem
