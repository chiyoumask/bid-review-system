<template>
  <div v-if="project">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px">
      <div>
        <h2 style="margin: 0">{{ project.name }}</h2>
        <span style="color: #999">编号：{{ project.bid_number || '未设置' }}</span>
      </div>
      <a-space>
        <a-button @click="$router.back()">返回列表</a-button>
        <a-button type="primary" @click="handleStartReview" :disabled="!canReview">
          <PlayCircleOutlined /> 开始审核
        </a-button>
      </a-space>
    </div>

    <a-row :gutter="16">
      <!-- Left: Documents -->
      <a-col :span="14">
        <a-card title="📄 项目文档" style="margin-bottom: 16px">
          <template #extra>
            <a-upload :before-upload="handleUpload" :show-upload-list="false" accept=".pdf,.docx,.doc,.txt">
              <a-button type="primary" size="small"><UploadOutlined /> 上传文档</a-button>
            </a-upload>
          </template>

          <a-empty v-if="!project.documents?.length" description="暂无文档，请上传评分标准和投标文件" />

          <a-table
            v-else
            :data-source="project.documents"
            :columns="docColumns"
            :pagination="false"
            size="small"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'doc_type'">
                <a-tag :color="record.doc_type === 'scoring_criteria' ? 'blue' : 'green'">
                  {{ docTypeText(record.doc_type) }}
                </a-tag>
              </template>
              <template v-if="column.dataIndex === 'status'">
                <a-badge :status="docStatusType(record.status)" :text="docStatusText(record.status)" />
              </template>
              <template v-if="column.dataIndex === 'action'">
                <a-button type="link" size="small" @click="handleReviewDoc(record)" :disabled="record.doc_type !== 'tender_doc' || record.status !== 'parsed'">
                  发起审核
                </a-button>
              </template>
            </template>
          </a-table>
        </a-card>

        <!-- Review Tasks -->
        <a-card title="🔍 审核记录">
          <a-empty v-if="!tasks.length" description="暂无审核记录" />
          <a-list v-else :data-source="tasks" item-layout="horizontal">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>
                    <a @click="$router.push(`/review/${item.id}`)">
                      {{ item.bidder_name || '投标文件 #' + item.bid_document_id }}
                    </a>
                  </template>
                  <template #description>
                    <span v-if="item.status === 'completed'">
                      预估得分：{{ item.estimated_score?.toFixed(1) }} / {{ item.total_possible_score }}
                      · 高风险 {{ item.risk_count_high }} | 中风险 {{ item.risk_count_medium }} | 低风险 {{ item.risk_count_low }}
                    </span>
                    <span v-else-if="item.status === 'analyzing'" style="color: #1890ff">分析中...</span>
                    <span v-else-if="item.status === 'error'" style="color: #ff4d4f">{{ item.error_message }}</span>
                    <span v-else>待处理</span>
                  </template>
                </a-list-item-meta>
                <template #actions>
                  <a-button type="link" @click="$router.push(`/review/${item.id}`)">查看</a-button>
                </template>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>

      <!-- Right: Scoring Criteria -->
      <a-col :span="10">
        <a-card title="⭐ 评分标准">
          <template #extra>
            <a-button size="small" @click="showAddCriteria = true">
              <PlusOutlined /> 手动添加
            </a-button>
          </template>

          <a-upload :before-upload="handleUploadCriteria" :show-upload-list="false" accept=".pdf,.docx,.doc,.txt">
            <a-button type="dashed" block style="margin-bottom: 16px">
              <UploadOutlined /> 上传评分标准文件（AI自动解析）
            </a-button>
          </a-upload>

          <a-empty v-if="!project.scoring_criteria?.length" description="请上传评分标准文件" />

          <div v-else>
            <div v-for="(group, gIdx) in criteriaGroups" :key="gIdx" style="margin-bottom: 16px">
              <h4 style="margin-bottom: 8px; color: #1890ff">{{ group.category }}</h4>
              <div v-for="item in group.items" :key="item.id"
                style="padding: 8px 12px; background: #fafafa; border-radius: 6px; margin-bottom: 4px; font-size: 13px">
                <div style="display: flex; justify-content: space-between">
                  <span>{{ item.item_name }}</span>
                  <a-tag color="orange">{{ item.max_score }}分</a-tag>
                </div>
                <div v-if="item.description" style="color: #999; margin-top: 4px; font-size: 12px">
                  {{ item.description }}
                </div>
              </div>
            </div>
          </div>

          <a-divider />
          <div style="text-align: center; color: #666">
            共 {{ project.scoring_criteria?.length || 0 }} 个评分项 ·
            总分 {{ totalScore }}
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- Add Criteria Modal -->
    <a-modal v-model:open="showAddCriteria" title="手动添加评分项" @ok="handleAddCriteria">
      <a-form :model="criteriaForm" layout="vertical">
        <a-form-item label="所属类别" required>
          <a-input v-model:value="criteriaForm.category" placeholder="如：资质条件、技术方案、商务条款、价格评分" />
        </a-form-item>
        <a-form-item label="评分项名称" required>
          <a-input v-model:value="criteriaForm.item_name" placeholder="如：企业资质等级" />
        </a-form-item>
        <a-form-item label="满分分值" required>
          <a-input-number v-model:value="criteriaForm.max_score" :min="0" :step="0.5" style="width: 100%" />
        </a-form-item>
        <a-form-item label="评分细则">
          <a-textarea v-model:value="criteriaForm.description" :rows="3" placeholder="具体的评分标准和条件" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Select Bid Document for Review -->
    <a-modal v-model:open="showSelectDoc" title="选择投标文件进行审核">
      <a-form layout="vertical">
        <a-form-item label="投标单位名称">
          <a-input v-model:value="reviewForm.bidder_name" placeholder="可选，填写投标单位名称" />
        </a-form-item>
        <a-form-item label="选择投标文件">
          <a-radio-group v-model:value="reviewForm.bid_document_id" style="width: 100%">
            <div v-for="doc in tenderDocs" :key="doc.id" style="padding: 8px">
              <a-radio :value="doc.id">{{ doc.filename }}</a-radio>
            </div>
          </a-radio-group>
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="showSelectDoc = false">取消</a-button>
        <a-button type="primary" @click="submitReview" :loading="submitting" :disabled="!reviewForm.bid_document_id">
          开始审核
        </a-button>
      </template>
    </a-modal>
  </div>

  <a-spin v-else spinning size="large" style="display: flex; justify-content: center; margin-top: 100px" />
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  UploadOutlined, PlusOutlined, PlayCircleOutlined,
} from '@ant-design/icons-vue'
import { projectsApi, type ProjectDetail, type Document, type ScoringCriteria } from '@/api/projects'
import { reviewApi, type ReviewTask } from '@/api/review'

const route = useRoute()
const router = useRouter()
const projectId = Number(route.params.id)

const project = ref<ProjectDetail | null>(null)
const tasks = ref<ReviewTask[]>([])
const showAddCriteria = ref(false)
const showSelectDoc = ref(false)
const submitting = ref(false)
let pollTimer: number | null = null

const criteriaForm = reactive({
  category: '', item_name: '', max_score: 10, description: '',
})
const reviewForm = reactive({
  bid_document_id: null as number | null,
  bidder_name: '',
})

const docColumns = [
  { title: '文件名', dataIndex: 'filename', ellipsis: true },
  { title: '类型', dataIndex: 'doc_type', width: 100 },
  { title: '状态', dataIndex: 'status', width: 100 },
  { title: '操作', dataIndex: 'action', width: 100 },
]

const tenderDocs = computed(() =>
  (project.value?.documents || []).filter(d => d.doc_type === 'tender_doc' && d.status === 'parsed')
)

const criteriaGroups = computed(() => {
  if (!project.value?.scoring_criteria) return []
  const groups: { category: string; items: ScoringCriteria[] }[] = []
  const map = new Map<string, ScoringCriteria[]>()
  for (const c of project.value.scoring_criteria) {
    if (!map.has(c.category)) map.set(c.category, [])
    map.get(c.category)!.push(c)
  }
  for (const [category, items] of map) {
    groups.push({ category, items })
  }
  return groups
})

const totalScore = computed(() =>
  (project.value?.scoring_criteria || []).reduce((sum, c) => sum + c.max_score, 0)
)

const canReview = computed(() =>
  tenderDocs.value.length > 0 && (project.value?.scoring_criteria?.length || 0) > 0
)

function docTypeText(type: string) {
  return { scoring_criteria: '评分标准', tender_doc: '投标文件', supplementary: '补充材料' }[type] || type
}
function docStatusType(status: string) {
  return { uploaded: 'default', parsing: 'processing', parsed: 'success', error: 'error' }[status] || 'default'
}
function docStatusText(status: string) {
  return { uploaded: '待解析', parsing: '解析中', parsed: '已解析', error: '解析失败' }[status] || status
}

async function loadProject() {
  project.value = await projectsApi.get(projectId)
}

async function loadTasks() {
  tasks.value = await reviewApi.listTasks(projectId)
}

async function handleUpload(file: File) {
  try {
    await projectsApi.uploadDocument(projectId, file, 'tender_doc')
    message.success(`${file.name} 上传成功，正在解析...`)
    setTimeout(loadProject, 1000)
  } catch (e: any) {
    message.error(e.response?.data?.detail || '上传失败')
  }
  return false
}

async function handleUploadCriteria(file: File) {
  try {
    await projectsApi.uploadDocument(projectId, file, 'scoring_criteria')
    message.success(`${file.name} 上传成功，AI正在解析评分标准...`)
    // Poll for completion
    setTimeout(loadProject, 3000)
    setTimeout(loadProject, 6000)
  } catch (e: any) {
    message.error(e.response?.data?.detail || '上传失败')
  }
  return false
}

async function handleAddCriteria() {
  if (!criteriaForm.category || !criteriaForm.item_name) {
    message.warning('请填写类别和名称')
    return
  }
  try {
    await projectsApi.createCriteria(projectId, criteriaForm)
    message.success('评分项已添加')
    showAddCriteria.value = false
    Object.assign(criteriaForm, { category: '', item_name: '', max_score: 10, description: '' })
    await loadProject()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '添加失败')
  }
}

function handleReviewDoc(doc: Document) {
  reviewForm.bid_document_id = doc.id
  reviewForm.bidder_name = ''
  showSelectDoc.value = true
}

function handleStartReview() {
  if (tenderDocs.value.length === 1) {
    reviewForm.bid_document_id = tenderDocs.value[0].id
    reviewForm.bidder_name = ''
    submitReview()
  } else {
    showSelectDoc.value = true
  }
}

async function submitReview() {
  if (!reviewForm.bid_document_id) return
  submitting.value = true
  try {
    const task = await reviewApi.createTask({
      project_id: projectId,
      bid_document_id: reviewForm.bid_document_id,
      bidder_name: reviewForm.bidder_name || undefined,
    })
    message.success('审核任务已创建，正在分析...')
    showSelectDoc.value = false
    await loadTasks()
    // Navigate to review workspace
    router.push(`/review/${task.id}`)
  } catch (e: any) {
    message.error(e.response?.data?.detail || '创建审核任务失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await loadProject()
  await loadTasks()
  // Poll for task status updates
  pollTimer = window.setInterval(async () => {
    const hasPending = tasks.value.some(t => t.status === 'analyzing' || t.status === 'pending')
    if (hasPending) {
      await loadTasks()
    }
  }, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
