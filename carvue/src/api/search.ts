import axios from 'axios';
// ✅ 引入现有的 IApiResponse 和刚才扩展的 ISearchResponseData
import type { IApiResponse, ISearchResponseData } from '@/types';

// --- 定义入参 (Params) ---
// 这个是搜索专用的，types 里没有，保留在这里定义即可
export interface SearchParams {
    q?: string;
    brand?: string;
    series_level?: string;
    energy_type?: string;
    min_price?: number;
    max_price?: number;
    sort_by?: 'default' | 'price_asc' | 'price_desc' | 'new';
    page: number;
    size: number;
}

// 创建 axios 实例 (建议后续移到 utils/request.ts)
const request = axios.create({
    baseURL: '/api/v1',
    timeout: 5000
});

// 搜索 API
// ✅ 泛型修正：使用 IApiResponse<ISearchResponseData>
export const searchCars = (params: SearchParams) => {
    return request.post<IApiResponse<ISearchResponseData>>('/search/cars', params);
};