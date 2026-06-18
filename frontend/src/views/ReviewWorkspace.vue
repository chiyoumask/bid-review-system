<template>
  <div v-if="task">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <div>
        <h2 style="margin: 0">
          <AuditOutlined /> 审核工作台
          <a-tag :color="task.status === 'completed' ? 'success' : task.status === 'analyzing' ? 'processing' : 'default'" style="margin-left: 8px">
            {{ statusText(task.status) }}
          </a-tag>
        </h2>
        <span style="color: #999; font-size: 13px">
          {{ task.bidder_name || '投标文件 #' + task.bid_document_id }}
        </span>
      </div>
      <a-space>
        <a-button @click="$router.back()">返回项目</a-button>
        <a-button v-if="task.status === 'completed'" type="primary" @click="handleFinalize">
          <CheckCircleOutlined /> 完成审核
        </a-button>
      </a-space>
    </div>

    <!-- Score Summary Bar -->
    <a-card v-if="task.status === 'completed'" size="small" style="margin-bottom: 16px">
      <a-row :gutter="24" align="middle">
        <a-col :span="6">
          <a-statistic
            title="预估总分"
            :value="task.estimated_score?.toFixed(1) || 0"
            :suffix="'/ ' + (task.total_possible_score || 0)"
            :value-style="{ fontSize: '24px', color: scoreColor }"
          />
        </a-col>
        <a-col :span="6">
          <a-progress
            type="circle"
            :percent="scorePercent"
            :stroke-color="scoreColor"
            :size="60"
            :format="() => scorePercent.toFixed(0) + '%'"
          />
        </a-col>
        <a-col :span="4">
          <a-statistic title="高风险" :value="task.risk_count_high" :value-style="{ color: '#ff4d4f' }" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="中风险" :value="task.risk_count_medium" :value-style="{ color: '#faad14' }" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="低风险" :value="task.risk_count_low" :value-style="{ color: '#52c41a' }" />
        </a-col>
      </a-row>
    </a-card>

    <!-- Analyzing animation -->
    <a-card v-if="task.status === 'analyzing'" style="text-align: center; padding: 60px 0">
      <a-spin size="large" />
      <p style="margin-top: 16px; color: #666">AI 正在分析投标文件，请稍候...</p>
    </a-card>

    <!-- Results -->
    <a-row v-if="task.status === 'completed' && results.length" :gutter="16">
      <a-col :span="16">
        <a-card title="逐项评审结果">
          <!-- Category tabs -->
          <a-tabs v-model:activeKey="activeCategory">
            <a-tab-pane v-for="cat in categories" :key="cat" :tab="cat">
              <div v-for="result in getResultsByCategory(cat)" :key="result.id" style="margin-bottom: 16px">
                <a-card size="small" :bordered="true"
                  :style="{ borderLeft: `4px solid ${riskColor(result.risk_level)}` }">
                  <div style="display: flex; justify-content: space-between; align-items: flex-start">
                    <div style="flex: 1">
                      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
                        <strong>{{ result.item_name }}</strong>
                        <a-tag :color="riskTagColor(result.risk_level)">{{ riskText(result.risk_level) }}</a-tag>
                        <span style="color: #999">满分 {{ result.max_score }}</span>
                      </div>

                      <a-collapse :bordered="false" ghost>
                        <a-collapse-panel key="analysis" header="AI 分析" style="padding: 0">
                          <p>{{ result.ai_analysis || '暂无分析' }}</p>
                        </a-collapse-panel>
                        <a-collapse-panel v-if="result.bid_content_excerpt" key="excerpt" header="原文摘录" style="padding: 0">
                          <div style="background: #f5f5f5; padding: 12px; border-radius: 4px; font-size: 13px; white-space: pre-wrap">
                            {{ result.bid_content_excerpt }}
                          </div>
                        </a-collapse-panel>
                        <a-collapse-panel v-if="result.risk_description" key="risk" header="风险说明" style="padding: 0">
                          <p style="color: #ff4d4f">{{ result.risk_description }}</p>
                        </a-collapse-panel>
                      </a-collapse>
                    </div>

                    <div style="margin-left: 16px; text-align: right; min-width: 100px">
                      <div style="font-size: 24px; font-weight: bold; color: #1890ff">
                        {{ result.ai_estimated_score?.toFixed(1) ?? '-' }}
                      </div>
                      <div style="color: #999; font-size: 12px">/ {{ result.max_score }}</div>
                    </div>
                  </div>

                  <!-- Human review -->
                  <a-divider style="margin: 12px 0" />
                  <div style="display: flex; align-items: center; gap: 8px">
                    <a-radio-group v-model:value="result._reviewer_status" size="small"
                      @change="handleResultUpdate(result)">
                      <a-radio-button value="confirmed">✓ 确认</a-radio-button>
                      <a-radio-button value="overridden">✎ 调整</a-radio-button>
                      <a-radio-button value="ignored">✗ 忽略</a-radio-button>
                    </a-radio-group>
                    <a-input-number
                      v-if="result._reviewer_status === 'overridden'"
                      v-model:value="result._reviewer_score"
                      :min="0" :max="result.max_score" :step="0.5" size="small" placeholder="调整分"
                      style="width: 90px"
                      @blur="handleResultUpdate(result)"
                    />
                    <a-input
                      v-if="result._reviewer_status !== 'pending'"
                      v-model:value="result._reviewer_comment"
                      size="small" placeholder="备注" style="flex: 1"
                      @blur="handleResultUpdate(result)"
                    />
                  </div>
                </a-card>
              </div>
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-col>

      <!-- Right: Summary -->
      <a-col :span="8">
        <a-card title="📋 审核总结" size="small" style="margin-bottom: 16px">
          <div style="white-space: pre-wrap; font-size: 13px">{{ task.summary || '暂无总结' }}</div>
        </a-card>

        <a-card title="📊 风险分布" size="small">
          <div v-for="cat in categories" :key="cat" style="margin-bottom: 12px">
            <div style="font-size: 13px; font-weight: bold; margin-bottom: 4px">{{ cat }}</div>
            <a-progress
              :percent="categoryScorePercent(cat)"
              :stroke-color="categoryScoreColor(cat)"
              size="small"
              :format="() => categoryScoreText(cat)"
            />
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>

  <a-spin v-else spinning size="large" style="display: flex; justify-content: center; margin-top: 100px" />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { AuditOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import { reviewApi, type ReviewTaskDetail, type ReviewResult } from '@/api/review'

const route = useRoute()
const taskId = Number(route.params.taskId)

const task = ref<ReviewTaskDetail | null>(null)
const activeCategory = ref('')

// Extend results with local review state
interface ResultWithReview extends ReviewResult {
  _reviewer_status: string
  _reviewer_score: number | null
  _reviewer_comment: string
}

const results = ref<ResultWithReview[]>([])

const categories = computed(() => {
  const cats = [...new Set(results.value.map(r => r.category))]
  return cats
})

const scorePercent = computed(() => {
  if (!task.value?.total_possible_score) return 0
  return ((task.value.estimated_score || 0) / task.value.total_possible_score) * 100
})

const scoreColor = computed(() => {
  const pct = scorePercent.value
  if (pct >= 80) return '#52c41a'
  if (pct >= 60) return '#faad14'
  return '#ff4d4f'
})

function statusText(status: string) {
  return { pending: '待处理', analyzing: '分析中', completed: '已完成', error: '出错' }[status] || status
}

function riskColor(level: string | null) {
  return { high: '#ff4d4f', medium: '#faad14', low: '#52c41a', none: '#d9d9d9' }[level || 'none']
}

function riskTagColor(level: string | null) {
  return { high: 'error', medium: 'warning', low: 'success', none: 'default' }[level || 'none']
}

function riskText(level: string | null) {
  return { high: '高风险', medium: '中风险', low: '低风险', none: '无风险' }[level || 'none']
}

function getResultsByCategory(cat: string) {
  return results.value.filter(r => r.category === cat)
}

function categoryScorePercent(cat: string) {
  const catResults = getResultsByCategory(cat)
  const max = catResults.reduce((s, r) => s + r.max_score, 0)
  const est = catResults.reduce((s, r) => s + (r.ai_estimated_score || 0), 0)
  return max > 0 ? (est / max) * 100 : 0
}

function categoryScoreColor(cat: string) {
  const pct = categoryScorePercent(cat)
  if (pct >= 80) return '#52c41a'
  if (pct >= 60) return '#faad14'
  return '#ff4d4f'
}

function categoryScoreText(cat: string) {
  const catResults = getResultsByCategory(cat)
  const max = catResults.reduce((s, r) => s + r.max_score, 0)
  const est = catResults.reduce((s, r) => s + (r.ai_estimated_score || 0), 0)
  return `${est.toFixed(1)} / ${max}`
}

async function handleResultUpdate(result: ResultWithReview) {
  try {
    await reviewApi.updateResult(result.id, {
      reviewer_status: result._reviewer_status,
      reviewer_score: result._reviewer_score || undefined,
      reviewer_comment: result._reviewer_comment || undefined,
    })
  } catch (e: any) {
    message.error('更新失败')
  }
}

async function handleFinalize() {
  try {
    const res = await reviewApi.finalizeTask(taskId)
    message.success(`审核完成！预估总分：${res.total_score.toFixed(1)} / ${res.total_possible}`)
    await loadTask()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

async function loadTask() {
  task.value = await reviewApi.getTask(taskId)
  results.value = (task.value.results || []).map(r => ({
    ...r,
    _reviewer_status: r.reviewer_status || 'pending',
    _reviewer_score: r.reviewer_score,
    _reviewer_comment: r.reviewer_comment || '',
  }))
  if (categories.value.length) {
    activeCategory.value = categories.value[0]
  }
}

onMounted(loadTask)
</script>
