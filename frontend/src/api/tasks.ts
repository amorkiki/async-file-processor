import client from "@/api/client";
import { type TaskCreate, type TaskOut, type TaskListResponse, type TaskStatus } from "@/api/types";

export const createTask = async (data: TaskCreate): Promise<{ task_id: string }> => {
  const response = await client.post('/tasks/', data);
  return response.data;
}

export const fetchTasks = async (params?: {
  status?: TaskStatus,
  page?: number,
  size?: number
}): Promise<TaskListResponse> => {
  const response = await client.get('/tasks/', { params });
  return response.data;
}

export const fetchTaskById = async (taskId: string): Promise<TaskOut> => {
  const response = await client.get(`/tasks/${taskId}`);
  return response.data;
}

export const cancelTask = async (taskId: string): Promise<void> => {
  await client.delete(`/tasks/${taskId}`);
}
