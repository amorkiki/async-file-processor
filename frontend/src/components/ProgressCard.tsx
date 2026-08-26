import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress";
import CancelTaskButton from "@/components/CancelTaskButton"

import type { TaskOut } from "@/api/types";

interface ProgressCardProps {
  activeTask: TaskOut;
  onCancel: () => void;
}

function ProgressCard({ activeTask, onCancel }: ProgressCardProps) {

  return (
    <Card className="h-[500px] flex flex-col">
      <CardHeader className="text-center">
        <CardTitle>实时进度</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col items-center justify-center p-6">
        {activeTask ? (
          <div className="flex flex-col items-center gap-4 w-full flex-1 justify-between">
            <div className="flex flex-col items-center gap-4 w-full">
              <div className="text-6xl font-bold text-primary">{activeTask.progress}%</div>
              <Progress value={activeTask.progress} className="w-full h-3" />
              <p className="text-sm text-muted-foreground">
                {activeTask.message || '任务处理中...'}
              </p>
            </div>
            <CancelTaskButton taskId={activeTask.id} onCancel={onCancel} className="w-full" />
          </div>
        ) : (<p className="text-muted-foreground">暂无进行中的任务</p>)}
      </CardContent>
    </Card>
  )
}

export default ProgressCard


