<template>
  <div>
    <h2 style="margin-bottom: 24px">📊 工作台</h2>

    <a-row :gutter="16" style="margin-bottom: 24px">
      <a-col :span="6">
        <a-card>
          <a-statistic title="项目总数" :value="stats.total_projects" :value-style="{ color: '#1890ff' }">
            <template #prefix><FolderOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="审核任务" :value="stats.total_tasks" :value-style="{ color: '#52c41a' }">
            <template #prefix><AuditOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="已完成" :value="stats.completed_tasks" :value-style="{ color: '#722ed1' }">
            <template #prefix><CheckCircleOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="高风险项" :value="stats.high_risk_count" :value-style="{ color: '#ff4d4f' }">
            <template #prefix><WarningOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="16">
      <a-col :span="12">
        <a-card title="最近项目">
          <template #extra>
            <a-button type="link" @click="$router.push('/projects')">查看全部</a-button>
          </template>
          <a-empty v-if="recentProjects.length === 0" description="暂无项目" />
          <a-list v-else :data-source="recentProjects" item-layout="horizontal">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>
                    <a @click="$router.push(`/projects/${item.id}`)">{{ item.name }}</a>
                  </template>
                  <template #description>
                    <span>{{ item.bid_number || '暂无编号' }} · {{ item.document_count }}个文件 · {{ item.task_count }}个审核任务</span>
                  </template>
                </a-list-item-meta>
                <template #actions>
                  <a-tag :color="statusColor(item.status)">{{ statusText(item.status) }}</a-tag>
                </template>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>

      <a-col :span="12">
        <a-card title="快速操作">
          <a-space direction="vertical" :size="12" style="width: 100%">
            <a-button type="primary" size="large" block @click="$router.push('/projects')">
              <PlusOutlined /> 新建审核项目
            </a-button>
            <a-button size="large" block @click="$router.push('/settings')">
              <SettingOutlined /> 配置 LLM 渠道
            </a-button>
          </a-space>

          <a-divider />

          <div style="color: #999; font-size: 13px">
            <p><strong>使用流程：</strong></p>
            <ol style="padding-left: 20px; margin: 0">
              <li>创建审核项目</li>
              <li>上传评分标准文件（AI自动解析）</li>
              <li>上传投标文件</li>
              <li>发起审核 → 查看评分比对结果</li>
              <li>人工复核 → 导出报告</li>
            </ol>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  FolderOutlined, AuditOutlined, CheckCircleOutlined,
  WarningOutlined, PlusOutlined, SettingOutlined,
} from '@ant-design/icons-vue'
import { settingsApi, type DashboardStats } from '@/api/settings'
import { useProjectStore } from '@/stores/project'
import type { Project } from '@/api/projects'

const projectStore = useProjectStore()
const stats = ref<DashboardStats>({ total_projects: 0, total_tasks: 0, completed_tasks: 0, high_risk_count: 0 })
const recentProjects = ref<Project[]>([])

function statusColor(status: string) {
  const map: Record<string, string> = { draft: 'default', analyzing: 'processing', completed: 'success', archived: 'default' }
  return map[status] || 'default'
}

function statusText(status: string) {
  const map: Record<string, string> = { draft: '草稿', analyzing: '分析中', completed: '已完成', archived: '已归档' }
  return map[status] || status
}

onMounted(async () => {
  try {
    stats.value = await settingsApi.getDashboard()
  } catch { /* ignore */ }
  await projectStore.fetchProjects()
  recentProjects.value = projectStore.projects.slice(0, 5)
})
</script>
