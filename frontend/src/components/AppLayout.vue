<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider v-model:collapsed="collapsed" :trigger="null" collapsible theme="dark" :width="220">
      <div class="logo">
        <span v-if="!collapsed">📋 智能审核</span>
        <span v-else>📋</span>
      </div>
      <a-menu theme="dark" mode="inline" v-model:selectedKeys="selectedKeys" @click="handleMenuClick">
        <a-menu-item key="/dashboard">
          <template #icon><DashboardOutlined /></template>
          <span>仪表盘</span>
        </a-menu-item>
        <a-menu-item key="/projects">
          <template #icon><FolderOutlined /></template>
          <span>项目管理</span>
        </a-menu-item>
        <a-menu-item key="/settings">
          <template #icon><SettingOutlined /></template>
          <span>系统设置</span>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header style="background: #fff; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 4px rgba(0,0,0,0.08)">
        <a-button type="text" @click="collapsed = !collapsed">
          <MenuUnfoldOutlined v-if="collapsed" />
          <MenuFoldOutlined v-else />
        </a-button>
        <div style="display: flex; align-items: center; gap: 12px">
          <a-tag color="green" v-if="healthOk">服务在线</a-tag>
          <a-tag color="red" v-else>服务离线</a-tag>
          <a-dropdown>
            <a-button type="text">
              <UserOutlined /> {{ authStore.user?.display_name || authStore.user?.username || '用户' }}
            </a-button>
            <template #overlay>
              <a-menu @click="handleUserMenu">
                <a-menu-item key="logout">
                  <LogoutOutlined /> 退出登录
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>

      <a-layout-content style="margin: 16px; padding: 24px; background: #fff; border-radius: 8px">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  DashboardOutlined, FolderOutlined, SettingOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined,
  UserOutlined, LogoutOutlined,
} from '@ant-design/icons-vue'
import axios from 'axios'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const collapsed = ref(false)
const healthOk = ref(true)

const selectedKeys = computed(() => {
  const path = route.path
  if (path.startsWith('/projects')) return ['/projects']
  if (path.startsWith('/settings')) return ['/settings']
  return ['/dashboard']
})

function handleMenuClick({ key }: { key: string }) {
  router.push(key)
}

function handleUserMenu({ key }: { key: string }) {
  if (key === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}

onMounted(async () => {
  try {
    await axios.get('/api/health')
  } catch {
    healthOk.value = false
  }
})
</script>

<style scoped>
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: bold;
  color: #fff;
  white-space: nowrap;
}
</style>
