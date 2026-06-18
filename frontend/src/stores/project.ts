import { defineStore } from 'pinia'
import { ref } from 'vue'
import { projectsApi, type Project, type ProjectDetail } from '@/api/projects'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<ProjectDetail | null>(null)
  const loading = ref(false)

  async function fetchProjects() {
    loading.value = true
    try {
      projects.value = await projectsApi.list()
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id: number) {
    loading.value = true
    try {
      currentProject.value = await projectsApi.get(id)
    } finally {
      loading.value = false
    }
  }

  async function createProject(data: { name: string; description?: string; bid_number?: string }) {
    const project = await projectsApi.create(data)
    projects.value.unshift(project)
    return project
  }

  async function deleteProject(id: number) {
    await projectsApi.delete(id)
    projects.value = projects.value.filter(p => p.id !== id)
  }

  return { projects, currentProject, loading, fetchProjects, fetchProject, createProject, deleteProject }
})
