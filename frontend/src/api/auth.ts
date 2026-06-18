import client from './client'

export interface User {
  id: number
  username: string
  email: string
  display_name: string | null
  role: string
  is_active: boolean
  created_at: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export const authApi = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const { data } = await client.post('/auth/login', { username, password })
    return data
  },

  async register(payload: {
    username: string
    email: string
    password: string
    display_name?: string
  }): Promise<User> {
    const { data } = await client.post('/auth/register', payload)
    return data
  },

  async getMe(): Promise<User> {
    const { data } = await client.get('/auth/me')
    return data
  },
}
