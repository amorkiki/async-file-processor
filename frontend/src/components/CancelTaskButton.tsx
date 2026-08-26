import { useState } from "react";
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";

interface CancelTaskButtonProps {
  taskId: string;
  onCancel: () => void;   // 取消成功后刷新列表
  variant?: "destructive" | "outline" | "ghost";
  size?: "default" | "sm" | "lg";
  className?: string;
  disabled?: boolean;
}

function CancelTaskButton({
  taskId,
  onCancel,
  variant = "destructive",
  size = "default",
  className = "",
  disabled = false,
}: CancelTaskButtonProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleCancelClick = () => {
    setIsDialogOpen(true);
  }

  const handleCancelConfirm = async () => {
    // if (!taskId) return;
    setIsLoading(true);
    try {
      const { cancelTask } = await import('@/api/tasks');
      await cancelTask(taskId);
      toast.success('任务已取消');
      onCancel();
    } catch (error) {
      toast.error(error.message || '取消失败');
    } finally {
      setIsLoading(false);
      setIsDialogOpen(false);
    }
  }

  return (
    <>
      <Button
        variant={variant}
        size={size}
        className={className}
        onClick={handleCancelClick}
        disabled={disabled || isLoading}
      >
        取消任务
      </Button>

      <AlertDialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认取消任务？</AlertDialogTitle>
            <AlertDialogDescription>
              此操作将停止该任务的执行，已处理的数据将不会保留。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>继续执行</AlertDialogCancel>
            <AlertDialogAction onClick={handleCancelConfirm} className="bg-destructive text-destructive-foreground hover:bg-destructive/90" disabled={disabled}>
              {isLoading ? '取消中...' : '确认取消'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

export default CancelTaskButton