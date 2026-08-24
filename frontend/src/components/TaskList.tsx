import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import TaskItem from '@/components/TaskItem';
import type { TaskOut } from '@/api/types';

interface TaskListProps {
  tasks: TaskOut[];
  onCancel: () => void;
}


function TaskList({ tasks, onCancel }: TaskListProps) {

  return (
    <Card>
      <CardHeader className="text-center">
        <CardTitle>任务记录</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 max-h-400px overflow-y-auto">
        {tasks.length === 0 ? (<p className="text-center text-muted-foreground">暂无任务</p>) : (
          tasks.map(task => (
            <TaskItem key={task.id} task={task} onCancel={onCancel}></TaskItem>
          ))
        )}
      </CardContent>
    </Card>
  )
}

export default TaskList
