import client from './client'

export interface Project {
  id: number
  name: string
  description: string | null
  bid_number: string | null
  status: string
  created_by: number
  created_at: string
  updated_at: string
  document_count: number
  task_count: number
}

export interface Document {
  id: number
  project_id: number
  doc_type: string
  filename: string
  file_size: number | null
  page_count: number | null
  status: string
  error_message: string | null
  created_at: string
}

export interface ScoringCriteria {
  id: number
  project_id: number
  category: string
  item_name: string
  max_score: number
  description: string | null
  evaluation_criteria: string | null
  sort_order: number
  created_at: string
}

export interface ProjectDetail extends Project {
  documents: Document[]
  scoring_criteria: ScoringCriteria[]
}

export const projectsApi = {
  async list(): Promise<Project[]> {
    const { data } = await client.get('/projects')
    return data
  },

  async get(id: number): Promise<ProjectDetail> {
    const { data } = await client.get(`/projects/${id}`)
    return data
  },

  async create(payload: { name: string; description?: string; bid_number?: string }): Promise<Project> {
    const { data } = await client.post('/projects', payload)
    return data
  },

  async delete(id: number): Promise<void> {
    await client.delete(`/projects/${id}`)
  },

  async uploadDocument(
    projectId: number,
    file: File,
    docType: string = 'tender_doc'
  ): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('doc_type', docType)
    const { data } = await client.post(`/projects/${projectId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async getCriteria(projectId: number): Promise<ScoringCriteria[]> {
    const { data } = await client.get(`/projects/${projectId}/criteria`)
    return data
  },

  async createCriteria(
    projectId: number,
    item: {
      category: string
      item_name: string
      max_score: number
      description?: string
      evaluation_criteria?: string
    }
  ): Promise<ScoringCriteria> {
    const { data } = await client.post(`/projects/${projectId}/criteria`, item)
    return data
  },

  async deleteCriteria(projectId: number, criteriaId: number): Promise<void> {
    await client.delete(`/projects/${projectId}/criteria/${criteriaId}`)
  },
}
