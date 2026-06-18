<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>📋 招投标文件智能审核系统</h1>
        <p>基于AI的评分标准驱动审核平台</p>
      </div>

      <a-tabs v-model:activeKey="activeTab" centered>
        <a-tab-pane key="login" tab="登录">
          <a-form :model="loginForm" @finish="handleLogin" layout="vertical">
            <a-form-item label="用户名" name="username" :rules="[{ required: true, message: '请输入用户名' }]">
              <a-input v-model:value="loginForm.username" size="large" placeholder="请输入用户名" />
            </a-form-item>
            <a-form-item label="密码" name="password" :rules="[{ required: true, message: '请输入密码' }]">
              <a-input-password v-model:value="loginForm.password" size="large" placeholder="请输入密码" />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" html-type="submit" size="large" block :loading="loading">
                登 录
              </a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>

        <a-tab-pane key="register" tab="注册">
          <a-form :model="registerForm" @finish="handleRegister" layout="vertical">
            <a-form-item label="用户名" name="username" :rules="[{ required: true }]">
              <a-input v-model:value="registerForm.username" size="large" placeholder="请输入用户名" />
            </a-form-item>
            <a-form-item label="邮箱" name="email" :rules="[{ required: true }, { type: 'email', message: '请输入有效邮箱' }]">
              <a-input v-model:value="registerForm.email" size="large" placeholder="请输入邮箱" />
            </a-form-item>
            <a-form-item label="显示名称" name="display_name">
              <a-input v-model:value="registerForm.display_name" size="large" placeholder="可选" />
            </a-form-item>
            <a-form-item label="密码" name="password" :rules="[{ required: true }, { min: 6, message: '密码至少6位' }]">
              <a-input-password v-model:value="registerForm.password" size="large" placeholder="请设置密码" />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" html-type="submit" size="large" block :loading="loading">
                注 册
              </a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>
      </a-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const activeTab = ref('login')

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '', display_name: '' })

async function handleLogin() {
  loading.value = true
  try {
    await authStore.login(loginForm.username, loginForm.password)
    message.success('登录成功')
    router.push('/dashboard')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  loading.value = true
  try {
    await authApi.register(registerForm)
    message.success('注册成功，请登录')
    activeTab.value = 'login'
    loginForm.username = registerForm.username
    loginForm.password = registerForm.password
  } catch (e: any) {
    message.error(e.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}
.login-header {
  text-align: center;
  margin-bottom: 32px;
}
.login-header h1 {
  font-size: 22px;
  margin-bottom: 8px;
}
.login-header p {
  color: #666;
  font-size: 14px;
}
</style>
