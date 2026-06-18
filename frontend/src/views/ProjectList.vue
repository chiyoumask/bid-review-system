<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px">
      <h2 style="margin: 0">📁 项目管理</h2>
      <a-button type="primary" @click="showCreateModal = true">
        <PlusOutlined /> 新建项目
      </a-button>
    </div>

    <a-spin :spinning="projectStore.loading">
      <a-empty v-if="projectStore.projects.length === 0 && !projectStore.loading" description="暂无项目，点击上方按钮创建" />

      <a-row :gutter="[16, 16]" v-else>
        <a-col :span="8" v-for="project in projectStore.projects" :key="project.id">
          <a-card hoverable @click="$router.push(`/projects/${project.id}`)">
            <template #title>
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span>{{ project.name }}</span>
                <a-tag :color="statusColor(project.status)">{{ statusText(project.status) }}</a-tag>
              </div>
            </template>

            <p v-if="project.bid_number" style="color: #666">编号：{{ project.bid_number }}</p>
            <p v-if="project.description" style="color: #999; font-size: 13px">{{ project.description }}</p>

            <template #actions>
              <span><FileOutlined /> {{ project.document_count }}</span>
              <span><AuditOutlined /> {{ project.task_count }}</span>
              <a-popconfirm title="确定删除此项目？" @confirm="handleDelete(project.id)" ok-text="删除" cancel-text="取消">
                <a-button type="text" danger size="small" @click.stop>删除</a-button>
              </a-popconfirm>
            </template>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>

    <!-- Create Project Modal -->
    <a-modal v-model:open="showCreateModal" title="新建审核项目" @ok="handleCreate" :confirm-loading="creating">
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="项目名称" required>
          <a-input v-model:value="createForm.name" placeholder="例：XX工程设计施工一体化项目" />
        </a-form-item>
        <a-form-item label="招标编号">
          <a-input v-model:value="createForm.bid_number" placeholder="可选" />
        </a-form-item>
        <a-form-item label="项目描述">
          <a-textarea v-model:value="createForm.description" :rows="3" placeholder="可选" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, FileOutlined, AuditOutlined } from '@ant-design/icons-vue'
import { useProjectStore } from '@/stores/project'

const projectStore = useProjectStore()
const showCreateModal = ref(false)
const creating = ref(false)
const createForm = reactive({ name: '', bid_number: '', description: '' })

function statusColor(status: string) {
  const map: Record<string, string> = { draft: 'default', analyzing: 'processing', completed: 'success', archived: 'default' }
  return map[status] || 'default'
}

function statusText(status: string) {
  const map: Record<string, string> = { draft: '草稿', analyzing: '分析中', completed: '已完成', archived: '已归档' }
  return map[status] || status
}

async function handleCreate() {
  if (!createForm.name.trim()) {
    message.warning('请输入项目名称')
    return
  }
  creating.value = true
  try {
    await projectStore.createProject(createForm)
    message.success('项目创建成功')
    showCreateModal.value = false
    Object.assign(createForm, { name: '', bid_number: '', description: '' })
  } catch (e: any) {
    message.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await projectStore.deleteProject(id)
    message.success('项目已删除')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(() => projectStore.fetchProjects())
</script>
