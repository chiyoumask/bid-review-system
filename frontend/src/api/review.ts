import client from './client'

export interface ReviewTask {
  id: number
  project_id: number
  bid_document_id: number
  bidder_name: string | null
  status: string
  total_possible_score: number | null
  estimated_score: number | null
  risk_count_high: number
  risk_count_medium: number
  risk_count_low: number
  summary: string | null
  error_message: string | null
  created_by: number
  created_at: string
  updated_at: string
}

export interface ReviewResult {
  id: number
  task_id: number
  criteria_id: number
  category: string
  item_name: string
  max_score: number
  ai_estimated_score: number | null
  ai_analysis: string | null
  risk_level: string | null
  risk_description: string | null
  bid_content_excerpt: string | null
  evidence_locations: any | null
  reviewer_status: string
  reviewer_score: number | null
  reviewer_comment: string | null
  reviewed_by: number | null
  reviewed_at: string | null
  created_at: string
}

export interface ReviewTaskDetail extends ReviewTask {
  results: ReviewResult[]
}

export const reviewApi = {
  async listTasks(projectId?: number): Promise<ReviewTask[]> {
    const params = projectId ? { project_id: projectId } : {}
    const { data } = await client.get('/review/tasks', { params })
    return data
  },

  async getTask(taskId: number): Promise<ReviewTaskDetail> {
    const { data } = await client.get(`/review/tasks/${taskId}`)
    return data
  },

  async createTask(payload: {
    project_id: number
    bid_document_id: number
    bidder_name?: string
  }): Promise<ReviewTask> {
    const { data } = await client.post('/review/tasks', payload)
    return data
  },

  async updateResult(
    resultId: number,
    payload: {
      reviewer_status: string
      reviewer_score?: number
      reviewer_comment?: string
    }
  ): Promise<void> {
    await client.put(`/review/results/${resultId}`, payload)
  },

  async finalizeTask(taskId: number): Promise<{ total_score: number; total_possible: number }> {
    const { data } = await client.post(`/review/tasks/${taskId}/finalize`)
    return data
  },
}
