// src/App.tsx
import { useCallback, useEffect, useState } from "react"
import { type TaskCreate, type TaskOut } from '@/api/types'
import { createTask, fetchTasks } from "@/api/tasks"
import { Toaster, toast } from 'sonner';
import { TooltipProvider } from "@/components/ui/tooltip"
import TaskForm from "@/components/TaskForm"
import ProgressCard from "@/components/ProgressCard"
import TaskList from "@/components/TaskList"


export default function Dashboard() {
  const [tasks, setTasks] = useState<TaskOut[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const refreshTasks = useCallback(async () => {
    try {
      const data = await fetchTasks();
      setTasks(data.items)
    } catch (error) {
      console.log('刷新列表失败:', error)
    }
  }, [])

  const handleSubmit = async (formData: TaskCreate) => {
    setLoading(true);
    try {
      const result = await createTask(formData);
      // result要插入新任务到最前面（后端按 created_at 降序，新任务应在前）
      // 构造 TaskOut 占位， 之后通过轮询刷新列表获取真实数据
      const tempTask: TaskOut = {
        id: result.task_id,
        type: formData.type,
        source_name: null,
        status: 'pending',
        progress: 0,
        message: null,
        created_at: new Date().toISOString(),
      }
      setTasks(prev => [tempTask, ...prev]);
      await refreshTasks();
      toast.success('任务已提交，正在处理中...');
    } catch (error) {
      toast.error(error.message || '提交失败，请重试')
    } finally {
      setLoading(false);
    }
  }

  // Polling:轮询 2秒
  useEffect(() => {
    refreshTasks();
    const interval = setInterval(refreshTasks, 2000);
    return () => clearInterval(interval)
  }, [refreshTasks])

  // 计算当前活跃任务（第一个非终态）
  const activeTask = tasks.find((task) => task.status === 'pending' || task.status === 'running')
  // const displayTask = activeTask || tasks[0];

  return (
    <>
      <TooltipProvider>
        <Toaster position="top-center" />
        <div className="min-h-screen bg-background p-8 flex flex-col items-center">
          <h1 className="text-2xl font-bold text-primary mb-10 tracking-wider">异步文件处理平台</h1>
          {/* 三栏布局 */}
          <main className="w-full max-w-6xl grid grid-cols-1 md:grid-cols-3 gap-6">
            <TaskForm onSubmit={handleSubmit} loading={loading}></TaskForm>
            <ProgressCard activeTask={activeTask} onCancel={refreshTasks}></ProgressCard>
            <TaskList tasks={tasks} onCancel={refreshTasks} ></TaskList>
          </main>
        </div>
      </TooltipProvider>
    </>

  )
}