import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { IUser } from '@/types'

export const useUserStore = defineStore('user', () => {
    // 状态
    const token = ref<string>('')
    const userInfo = ref<IUser | null>(null)

    // 模拟登录 Action
    const login = async (phone: string, code: string): Promise<boolean> => {
        // 模拟网络请求延迟
        await new Promise(resolve => setTimeout(resolve, 1000))

        // 模拟登录成功，设置 Mock 数据
        token.value = 'mock-token-' + Date.now()
        userInfo.value = {
            id: '8402',
            nickname: '开开心心柚子8402',
            avatar: 'https://via.placeholder.com/80x80/FF6B9D/FFFFFF?text=U',
            phone: phone, // 使用输入的手机号
            gender: 'male',
            level: 1,
            experience: 100,
            nextLevelExperience: 200,
            badges: [],
            certifications: [],
            followingCount: 5,
            followerCount: 0,
            likeCount: 0,
            postCount: 0,
            favoriteCarIds: [],
            browseHistory: [],
            city: '北京',
            signature: '这人很懒，什么都没写',
            registeredAt: Date.now(),
            lastLoginAt: Date.now(),
            isVip: false
        }
        return true
    }

    // 登出 Action
    const logout = () => {
        token.value = ''
        userInfo.value = null
    }

    return {
        token,
        userInfo,
        login,
        logout
    }
}, {
    persist: true // 开启持久化存储
})