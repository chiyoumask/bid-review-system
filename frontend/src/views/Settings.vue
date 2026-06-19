<template>
  <div>
    <h2 style="margin-bottom: 24px">⚙️ 系统设置</h2>

    <a-row :gutter="16">
      <a-col :span="14">
        <a-card title="🤖 LLM 渠道配置">
          <template #extra>
            <a-button type="primary" size="small" @click="showAddProvider = true">
              <PlusOutlined /> 添加渠道
            </a-button>
          </template>

          <a-empty v-if="!providers.length" description="暂无渠道配置" />

          <a-table v-else :data-source="providers" :columns="providerColumns" :pagination="false" size="small" row-key="id">
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'provider_type'">
                <a-tag>{{ providerTypeText(record.provider_type) }}</a-tag>
              </template>
              <template v-if="column.dataIndex === 'is_active'">
                <a-badge :status="record.is_active ? 'success' : 'default'" :text="record.is_active ? '启用' : '禁用'" />
              </template>
              <template v-if="column.dataIndex === 'action'">
                <a-space>
                  <a-button type="link" size="small" @click="handleTestProvider(record)" :loading="testing === record.id">
                    测试连接
                  </a-button>
                  <a-popconfirm title="确定删除？" @confirm="handleDeleteProvider(record.id)">
                    <a-button type="link" danger size="small">删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>

          <a-alert v-if="testResult" :type="testResult.success ? 'success' : 'error'" style="margin-top: 16px" show-icon>
            <template #message>{{ testResult.success ? '连接成功' : '连接失败' }}</template>
            <template #description>{{ testResult.success ? testResult.response : testResult.error }}</template>
          </a-alert>
        </a-card>

        <a-card title="💡 使用说明" style="margin-top: 16px">
          <a-typography>
            <p><strong>支持的 LLM 渠道类型：</strong></p>
            <ul>
              <li><strong>DeepSeek</strong>：Base URL 为 <code>https://api.deepseek.com/v1</code>，模型名 <code>deepseek-chat</code></li>
              <li><strong>通义千问</strong>：Base URL 为 <code>https://dashscope.aliyuncs.com/compatible-mode/v1</code></li>
              <li><strong>OpenAI</strong>：Base URL 为 <code>https://api.openai.com/v1</code></li>
              <li><strong>自定义</strong>：任何 OpenAI 兼容接口均可</li>
            </ul>
            <p><strong>配置流程：</strong></p>
            <ol>
              <li>点击「添加渠道」，填写 API Key、Base URL、模型名</li>
              <li>点击「测试连接」验证配置是否正确</li>
              <li>启用渠道后即可使用系统</li>
            </ol>
          </a-typography>
        </a-card>
      </a-col>

      <a-col :span="10">
        <a-card title="📊 系统信息">
          <a-descriptions :column="1" size="small" bordered>
            <a-descriptions-item label="系统版本">v1.0.0</a-descriptions-item>
            <a-descriptions-item label="前端框架">Vue 3 + Ant Design Vue</a-descriptions-item>
            <a-descriptions-item label="后端框架">FastAPI + SQLAlchemy</a-descriptions-item>
            <a-descriptions-item label="数据库">PostgreSQL</a-descriptions-item>
            <a-descriptions-item label="AI 引擎">LLM API（远程推理）</a-descriptions-item>
          </a-descriptions>
        </a-card>
      </a-col>
    </a-row>

    <!-- Add Provider Modal -->
    <a-modal v-model:open="showAddProvider" title="添加 LLM 渠道" @ok="handleAddProvider" :confirm-loading="adding">
      <a-form :model="providerForm" layout="vertical">
        <a-form-item label="渠道名称" required>
          <a-input v-model:value="providerForm.name" placeholder="如：DeepSeek-主力" />
        </a-form-item>
        <a-form-item label="渠道类型" required>
          <a-select v-model:value="providerForm.provider_type">
            <a-select-option value="deepseek">DeepSeek</a-select-option>
            <a-select-option value="qwen">通义千问</a-select-option>
            <a-select-option value="openai">OpenAI</a-select-option>
            <a-select-option value="custom">自定义</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="API Key" required>
          <a-input-password v-model:value="providerForm.api_key" placeholder="sk-..." />
        </a-form-item>
        <a-form-item label="Base URL" required>
          <a-input v-model:value="providerForm.base_url" :placeholder="defaultBaseUrl" />
        </a-form-item>
        <a-form-item label="模型名称" required>
          <a-input v-model:value="providerForm.model_name" :placeholder="defaultModelName" />
        </a-form-item>
        <a-form-item label="优先级">
          <a-input-number v-model:value="providerForm.priority" :min="0" :max="100" />
          <div style="color: #999; font-size: 12px">数字越小优先级越高</div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { settingsApi, type LLMProvider } from '@/api/settings'

const providers = ref<LLMProvider[]>([])
const showAddProvider = ref(false)
const adding = ref(false)
const testing = ref<number | null>(null)
const testResult = ref<{ success: boolean; response?: string; error?: string } | null>(null)

const providerForm = reactive({
  name: '',
  provider_type: 'deepseek',
  api_key: '',
  base_url: '',
  model_name: '',
  is_active: true,
  priority: 0,
})

const defaultBaseUrl = computed(() => {
  const map: Record<string, string> = {
    deepseek: 'https://api.deepseek.com/v1',
    qwen: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    openai: 'https://api.openai.com/v1',
    custom: '',
  }
  return map[providerForm.provider_type] || ''
})

const defaultModelName = computed(() => {
  const map: Record<string, string> = {
    deepseek: 'deepseek-chat',
    qwen: 'qwen-plus',
    openai: 'gpt-4o',
    custom: '',
  }
  return map[providerForm.provider_type] || ''
})

const providerColumns = [
  { title: '名称', dataIndex: 'name', width: 140 },
  { title: '类型', dataIndex: 'provider_type', width: 100 },
  { title: '模型', dataIndex: 'model_name', ellipsis: true },
  { title: '状态', dataIndex: 'is_active', width: 80 },
  { title: '操作', dataIndex: 'action', width: 160 },
]

function providerTypeText(type: string) {
  return { deepseek: 'DeepSeek', qwen: '通义千问', openai: 'OpenAI', custom: '自定义' }[type] || type
}

async function loadProviders() {
  providers.value = await settingsApi.listLLMProviders()
}

async function handleAddProvider() {
  const payload = {
    ...providerForm,
    base_url: providerForm.base_url || defaultBaseUrl.value,
    model_name: providerForm.model_name || defaultModelName.value,
  }
  if (!payload.name || !payload.api_key || !payload.base_url || !payload.model_name) {
    message.warning('请填写必要字段')
    return
  }
  adding.value = true
  try {
    await settingsApi.addLLMProvider(payload as LLMProvider)
    message.success('渠道已添加')
    showAddProvider.value = false
    Object.assign(providerForm, { name: '', api_key: '', base_url: '', model_name: '' })
    await loadProviders()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '添加失败')
  } finally {
    adding.value = false
  }
}

async function handleDeleteProvider(id: number) {
  await settingsApi.deleteLLMProvider(id)
  message.success('已删除')
  await loadProviders()
}

async function handleTestProvider(provider: LLMProvider) {
  if (!provider.id) return
  testing.value = provider.id
  testResult.value = null
  try {
    testResult.value = await settingsApi.testLLMProvider(provider.id)
  } catch {
    testResult.value = { success: false, error: '测试请求失败' }
  } finally {
    testing.value = null
  }
}

onMounted(loadProviders)
</script>
