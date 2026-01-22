// 对应后端的 AuthFactory 策略 Key
export type LoginType = 'password' | 'sms' | 'dingtalk'

// 基础 Payload 接口
export interface IAuthPayload {
    [key: string]: any
}

// 策略 1: 账密登录 Payload
export interface IPasswordPayload extends IAuthPayload {
    account: string  // ✅ 修正: username -> account
    password: string
}

// 策略 2: 短信验证码 Payload
export interface ISmsPayload extends IAuthPayload {
    phone: string
    code: string
}

// 策略 3: 钉钉登录 Payload
export interface IDingTalkPayload extends IAuthPayload {
    auth_code: string
}

// 统一提交给后端 /api/v1/auth/login 的结构
export interface ILoginRequest {
    login_type: LoginType
    payload: IPasswordPayload | ISmsPayload | IDingTalkPayload
}

// 登录响应结构 (Token)
export interface ILoginResponse {
    access_token: string
    refresh_token: string
    login_type: string
    user_id: number
}