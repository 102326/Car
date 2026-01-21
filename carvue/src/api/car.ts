import axios from 'axios';
import type { IApiResponse, ICarProduct } from '@/types';

// 复用 ICarProduct，或者你可以定义一个更详细的 ICarDetail 继承它
// 这里为了简单，我们直接用 ICarProduct，因为它包含 images 等字段

const request = axios.create({
    baseURL: '/api/v1',
    timeout: 5000
});

export const getCarDetail = (id: string | number) => {
    return request.get<IApiResponse<ICarProduct>>(`/cars/${id}`);
};