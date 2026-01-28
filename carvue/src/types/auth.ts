// 对应后端的 AuthFactory 策略 Key
export type LoginType = 'password' | 'sms' | 'dingtalk'

/**
 * 统一登录请求结构 (扁平化，与后端 LoginParam 严格对应)
 * 后端 Schema: carfast/app/schemas/auth.py -> LoginParam
 */
export interface ILoginRequest {
    login_type: LoginType
    // 密码登录字段
    account?: string   // 账号(手机/邮箱)
    password?: string  // 密码
    // 短信/钉钉登录字段
    phone?: string     // 手机号
    code?: string      // 验证码/钉钉Code
}

// 登录响应结构 (对应后端 Token)
export interface ILoginResponse {
    access_token: string
    token_type: string
    user_name: string
}

// 用户信息响应 (对应后端 UserInfo)
export interface IUserInfo {
    id: number
    username?: string
    nickname?: string
    avatar?: string
    roles: string[]
}