/**
 * 易车 App 核心业务实体类型定义
 * @description 包含所有核心数据模型的 TypeScript 接口定义
 * @module types
 */

/**
 * 车型产品信息接口
 * @description 包含车型的基本信息、价格、配置等核心数据
 */
export interface ICarProduct {
  /** 车型唯一标识 */
  readonly id: string;
  /** 品牌名称 */
  brandName: string;
  /** 车系名称 */
  seriesName: string;
  /** 车型完整名称 */
  modelName: string;
  /** 官方指导价区间 [最低价, 最高价] (单位：万元) */
  priceRange: [number, number];
  /** 是否为新能源车型 */
  isNewEnergy: boolean;
  /** 能源类型：汽油、纯电动、插电混动、增程式等 */
  energyType: 'gasoline' | 'electric' | 'phev' | 'erev' | 'hybrid';
  /** 车型主图 URL */
  coverImage: string;
  /** 车型图片集 */
  images: string[];
  /** 车身结构：轿车、SUV、MPV等 */
  bodyType: string;
  /** 座位数 */
  seats: number;
  /** 排量 (单位：L，纯电车为 null) */
  displacement: number | null;
  /** 变速箱类型 */
  transmission: string;
  /** 续航里程 (单位：km，仅新能源车型) */
  endurance?: number;
  /** 快充时间 (单位：小时，仅新能源车型) */
  fastChargeTime?: number;
  /** 百公里加速时间 (单位：秒) */
  acceleration: number;
  /** 综合油耗/电耗 */
  fuelConsumption: string;
  /** 上市时间 (ISO 8601 格式) */
  launchDate: string;
  /** 在售状态 */
  onSale: boolean;
  /** 销量统计 (月销量) */
  monthlySales: number;
  /** 热度评分 (0-100) */
  hotScore: number;
  /** 用户评分 (0-5) */
  userRating: number;
  /** 评价数量 */
  reviewCount: number;
  /** 国家补贴金额 (单位：万元，仅新能源车型) */
  subsidy?: number;
  /** 品牌 Logo URL */
  brandLogo: string;
  /** 厂商类型：合资、自主、进口 */
  manufacturer: 'joint' | 'domestic' | 'import';
  /** 创建时间戳 */
  readonly createdAt: number;
  /** 更新时间戳 */
  updatedAt: number;
}

/**
 * 用户信息接口
 * @description 包含用户基本信息、等级、勋章等数据
 */
export interface IUser {
  /** 用户唯一标识 */
  readonly id: string;
  /** 用户昵称 */
  nickname: string;
  /** 用户头像 URL */
  avatar: string;
  /** 手机号 (脱敏) */
  phone: string;
  /** 性别：男、女、未知 */
  gender: 'male' | 'female' | 'unknown';
  /** 用户等级 (1-10) */
  level: number;
  /** 经验值 */
  experience: number;
  /** 升级所需经验值 */
  nextLevelExperience: number;
  /** 勋章列表 */
  badges: IBadge[];
  /** 已认证标签：车主认证、专业认证等 */
  certifications: string[];
  /** 关注数 */
  followingCount: number;
  /** 粉丝数 */
  followerCount: number;
  /** 获赞总数 */
  likeCount: number;
  /** 发帖数 */
  postCount: number;
  /** 收藏的车型 ID 列表 */
  favoriteCarIds: string[];
  /** 浏览足迹 ID 列表 */
  browseHistory: string[];
  /** 所在城市 */
  city: string;
  /** 个性签名 */
  signature: string;
  /** 注册时间戳 */
  readonly registeredAt: number;
  /** 最后登录时间戳 */
  lastLoginAt: number;
  /** VIP 状态 */
  isVip: boolean;
  /** VIP 到期时间戳 */
  vipExpireAt?: number;
}

/**
 * 用户勋章接口
 * @description 用户获得的成就勋章
 */
export interface IBadge {
  /** 勋章 ID */
  readonly id: string;
  /** 勋章名称 */
  name: string;
  /** 勋章图标 URL */
  icon: string;
  /** 勋章描述 */
  description: string;
  /** 获得时间戳 */
  obtainedAt: number;
  /** 是否为稀有勋章 */
  isRare: boolean;
}

/**
 * 资讯帖子接口
 * @description 包含用户发布的文章、视频、问答等内容
 */
export interface IReviewPost {
  /** 帖子唯一标识 */
  readonly id: string;
  /** 帖子类型：文章、视频、图文、问答 */
  type: 'article' | 'video' | 'image' | 'qa';
  /** 帖子标题 */
  title: string;
  /** 帖子内容 (Markdown 格式) */
  content: string;
  /** 摘要 */
  summary: string;
  /** 封面图 URL */
  coverImage: string;
  /** 媒体资源列表 (图片/视频 URL) */
  mediaList: IMediaItem[];
  /** 关联车型 ID */
  relatedCarId?: string;
  /** 关联车型信息快照 */
  relatedCar?: Pick<ICarProduct, 'id' | 'modelName' | 'brandName' | 'coverImage'>;
  /** 作者信息 */
  author: IAuthor;
  /** 标签列表 */
  tags: string[];
  /** 栏目分类：推荐、热榜、新车、导购、用车等 */
  category: string;
  /** 浏览量 */
  viewCount: number;
  /** 点赞数 */
  likeCount: number;
  /** 评论数 */
  commentCount: number;
  /** 收藏数 */
  favoriteCount: number;
  /** 转发数 */
  shareCount: number;
  /** 是否精华帖 */
  isHighlight: boolean;
  /** 是否置顶 */
  isPinned: boolean;
  /** 是否包含视频 */
  hasVideo: boolean;
  /** 视频时长 (单位：秒，仅视频类型) */
  videoDuration?: number;
  /** 发布状态：草稿、已发布、已删除 */
  status: 'draft' | 'published' | 'deleted';
  /** 发布时间戳 */
  publishedAt: number;
  /** 创建时间戳 */
  readonly createdAt: number;
  /** 更新时间戳 */
  updatedAt: number;
}

/**
 * 媒体项接口
 * @description 帖子中的图片或视频资源
 */
export interface IMediaItem {
  /** 媒体 ID */
  readonly id: string;
  /** 媒体类型 */
  type: 'image' | 'video';
  /** 媒体 URL */
  url: string;
  /** 缩略图 URL */
  thumbnail?: string;
  /** 宽度 (像素) */
  width: number;
  /** 高度 (像素) */
  height: number;
  /** 时长 (秒，仅视频) */
  duration?: number;
  /** 文件大小 (字节) */
  size: number;
}

/**
 * 作者信息接口
 * @description 帖子作者的简要信息
 */
export interface IAuthor {
  /** 用户 ID */
  readonly id: string;
  /** 昵称 */
  nickname: string;
  /** 头像 URL */
  avatar: string;
  /** 用户等级 */
  level: number;
  /** 认证标签 */
  certifications: string[];
  /** 是否关注 */
  isFollowed: boolean;
}

/**
 * 二手车信息接口
 * @description 二手车交易相关数据
 */
export interface IUsedCar {
  /** 二手车唯一标识 */
  readonly id: string;
  /** 车型基本信息 */
  carInfo: Pick<ICarProduct, 'brandName' | 'seriesName' | 'modelName' | 'coverImage'>;
  /** 上牌时间 (ISO 8601 格式) */
  registrationDate: string;
  /** 行驶里程 (单位：万公里) */
  mileage: number;
  /** 一口价 (单位：万元) */
  price: number;
  /** 原车指导价 (单位：万元) */
  originalPrice: number;
  /** 所在城市 */
  city: string;
  /** 车况描述 */
  condition: string;
  /** 车况等级：优秀、良好、一般 */
  conditionLevel: 'excellent' | 'good' | 'fair';
  /** 过户次数 */
  transferCount: number;
  /** 是否发生过重大事故 */
  hasAccident: boolean;
  /** 年检到期日期 */
  inspectionExpireDate: string;
  /** 保险到期日期 */
  insuranceExpireDate: string;
  /** 车辆图片列表 */
  images: string[];
  /** 卖家信息 */
  seller: ISeller;
  /** 浏览量 */
  viewCount: number;
  /** 发布时间戳 */
  publishedAt: number;
  /** 更新时间戳 */
  updatedAt: number;
}

/**
 * 卖家信息接口
 * @description 二手车卖家的简要信息
 */
export interface ISeller {
  /** 卖家 ID */
  readonly id: string;
  /** 卖家类型：个人、车商 */
  type: 'individual' | 'dealer';
  /** 卖家名称 */
  name: string;
  /** 联系电话 */
  phone: string;
  /** 所在地区 */
  location: string;
  /** 认证状态 */
  isVerified: boolean;
}

/**
 * 评论接口
 * @description 帖子或车型的评论数据
 */
export interface IComment {
  /** 评论唯一标识 */
  readonly id: string;
  /** 帖子/车型 ID */
  targetId: string;
  /** 目标类型：帖子、车型 */
  targetType: 'post' | 'car';
  /** 评论内容 */
  content: string;
  /** 评论者信息 */
  author: IAuthor;
  /** 父评论 ID (回复时) */
  parentId?: string;
  /** 点赞数 */
  likeCount: number;
  /** 回复数 */
  replyCount: number;
  /** 创建时间戳 */
  readonly createdAt: number;
}

/**
 * 搜索历史接口
 * @description 用户的搜索记录
 */
export interface ISearchHistory {
  /** 记录 ID */
  readonly id: string;
  /** 搜索关键词 */
  keyword: string;
  /** 搜索类型：车型、内容、二手车 */
  type: 'car' | 'content' | 'used-car';
  /** 搜索时间戳 */
  readonly searchedAt: number;
}

/**
 * API 响应基础接口
 * @description 所有 API 返回数据的统一格式
 */
export interface IApiResponse<T = unknown> {
  /** 响应状态码 */
  code: number;
  /** 响应消息 */
  message: string;
  /** 响应数据 */
  data: T;
  /** 请求追踪 ID */
  traceId?: string;
  /** 时间戳 */
  timestamp: number;
}

/**
 * 分页请求参数接口
 * @description 列表接口的分页参数
 */
export interface IPaginationParams {
  /** 页码 (从 1 开始) */
  page: number;
  /** 每页数量 */
  pageSize: number;
  /** 排序字段 */
  sortBy?: string;
  /** 排序方向：升序、降序 */
  sortOrder?: 'asc' | 'desc';
}

/**
 * 分页响应数据接口
 * @description 列表接口的分页响应格式
 */
export interface IPaginationResponse<T = unknown> {
  /** 数据列表 */
  list: T[];
  /** 总记录数 */
  total: number;
  /** 当前页码 */
  page: number;
  /** 每页数量 */
  pageSize: number;
  /** 总页数 */
  totalPages: number;
  /** 是否有下一页 */
  hasMore: boolean;
}

/**
 * 筛选条件接口
 * @description 智能选车的筛选参数
 */
export interface ICarFilter {
  /** 价格区间 (单位：万元) */
  priceRange?: [number, number];
  /** 品牌 ID 列表 */
  brandIds?: string[];
  /** 能源类型列表 */
  energyTypes?: ICarProduct['energyType'][];
  /** 车身结构列表 */
  bodyTypes?: string[];
  /** 座位数列表 */
  seats?: number[];
  /** 是否仅新能源 */
  newEnergyOnly?: boolean;
  /** 排序方式：热度、价格、销量 */
  sortBy?: 'hotScore' | 'price' | 'sales';
}

/**
 * AI 助手响应接口
 * @description AI 智能推荐的结构化数据
 */
export interface IAIAssistResponse {
  /** 推荐车型列表 */
  recommendedCars: ICarProduct[];
  /** 分析维度 */
  analysis: {
    /** 外观设计评价 */
    appearance: string;
    /** 动力性能评价 */
    power: string;
    /** 操控性能评价 */
    handling: string;
    /** 安全配置评价 */
    safety: string;
    /** 性价比评价 */
    costPerformance: string;
  };
  /** 推荐理由 (Markdown 格式) */
  reason: string;
  /** 置信度 (0-1) */
  confidence: number;
}

