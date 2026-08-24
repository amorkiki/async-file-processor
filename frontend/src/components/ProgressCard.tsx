import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress";
import { toast } from 'sonner';
import type { TaskOut } from "@/api/types";

interface ProgressCardProps {
  activeTask: TaskOut;
  onCancel: () => void;
}

function ProgressCard({ activeTask, onCancel }: ProgressCardProps) {
  const handleCancel = async () => {
    if (!activeTask) return;
    if (window.confirm('确认取消该任务？')) {
      try {
        const { cancelTask } = await import('@/api/tasks');
        await cancelTask(activeTask.id);
        toast.success('任务已取消');
        onCancel();
      } catch (error) {
        toast.error(error.message || '取消失败');
      }
    }
  }

  return (
    <Card>
      <CardHeader className="text-center">
        <CardTitle>实时进度</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4">
        {activeTask ? (
          <>
            <div className="text-6xl font-bold text-primary">{activeTask.progress}%</div>
            <Progress value={activeTask.progress} className="w-full h-3" />
            <p className="text-sm text-muted-foreground">
              {activeTask.message || '任务处理中...'}
            </p>
            <Button
              variant="destructive"
              className="w-full"
              onClick={handleCancel}
              disabled={activeTask.status === 'cancelled'}
            >
              取消任务
            </Button>
          </>
        ) : (<p className="text-muted-foreground">暂无进行中的任务</p>)}
      </CardContent>
    </Card>
  )
}

export default ProgressCard


