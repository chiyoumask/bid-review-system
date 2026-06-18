import client from './client'

export interface DashboardStats {
  total_projects: number
  total_tasks: number
  completed_tasks: number
  high_risk_count: number
}

export interface LLMProvider {
  id?: number
  name: string
  provider_type: string
  api_key?: string
  base_url: string
  model_name: string
  is_active: boolean
  priority: number
}

export const settingsApi = {
  async getDashboard(): Promise<DashboardStats> {
    const { data } = await client.get('/settings/dashboard')
    return data
  },

  async listLLMProviders(): Promise<LLMProvider[]> {
    const { data } = await client.get('/settings/llm-providers')
    return data
  },

  async addLLMProvider(provider: LLMProvider): Promise<LLMProvider> {
    const { data } = await client.post('/settings/llm-providers', provider)
    return data
  },

  async deleteLLMProvider(id: number): Promise<void> {
    await client.delete(`/settings/llm-providers/${id}`)
  },

  async testLLMProvider(id: number): Promise<{ success: boolean; response?: string; error?: string }> {
    const { data } = await client.post(`/settings/llm-providers/${id}/test`)
    return data
  },
}
