# 🚗 CarFast API Backend

## ⚠️ 核心红线 (不看必踩坑)

1. **钱包保护**: 涉及到私人 API 的 Key (如 DeepSeek, 七牛云) **一定要写到 `.env` 中**。

   > 除非你喜欢当“公交车”，让全网爬虫用你的钱跑测试。
   >
2. **公共配置**: 非私人的公用 Key (如数据库 Host、RabbitMQ 默认端口) 写到 `config.py`。
3. **IDE 调教**: 更新完 `requirements.txt` 或环境后，记得在 PyCharm 右下角刷新一下 Python 软件包。

   > Conda 比较笨，不会自己扫描，别怪代码爆红。
   >
4. **数据库模式 (Schema)**:

   > 本项目**强制使用 `car` 模式**，不要把表建在 `public` 下！
   > 这里的代码和 CDC 监听器都只认 `car`，写错地方就是“肉包子打狗——有去无回”。
   >

---

## 📂 项目结构 (2026 Refactored)

```text
carfast
├── app
│   ├── api             # 路由入口 (v1/auth, v1/search, v1/cms)
│   ├── consumers       # [核心] 消息消费者 (CDC 实时同步监听器在此)
│   ├── core            # 基础设施 (DB引擎, ES连接, MQ连接, CeleryApp)
│   ├── jobs            # [维护] 跑批作业 (原 scripts 里的全量同步脚本移到这了)
│   ├── models          # ORM 模型 (SQLAlchemy)
│   ├── schemas         # Pydantic 校验模型 (入参/出参)
│   ├── services        # 业务逻辑层 (ES写入封装, Auth策略, 公共组件)
│   ├── tasks           # Celery 异步任务 (发送通知, 耗时操作)
│   ├── utils           # 工具箱 (JWT, 密码哈希, 第三方SDK)
│   └── config.py       # 全局配置表
├── ops                 # [运维] 部署与初始化
│   └── debezium        # CDC 连接器注册脚本 (部署时跑一次)
├── scripts             # [暂存] 临时测试脚本 (用完即删，别当仓库用)
├── static              # 静态资源
├── uploads             # 文件上传临时目录
├── .env                # 秘密基地 (.gitignore 已忽略)
├── main.py             # 启动入口
└── requirements.txt    # 依赖清单
```


## ⚡️ 关键服务说明

### 1. 数据同步链路 (CDC)

本项目不再依赖业务代码发 MQ 做同步，而是采用 **"PostgreSQL -> Debezium -> Kafka -> Consumer -> ES"** 的实时架构。

* **实时同步**: 靠 `app/consumers/cdc_sync.py` 监听 Kafka。
* **全量洗地**: 靠 `app/jobs/full_sync_es.py` 直接查库批量灌入。
* **初始化**: 部署后需运行 `ops/debezium/init_connector.py` 激活监听器。

### 2. 搜索引擎 (Elasticsearch)

* **分词器**: 必须安装 `ik_max_word` (analysis-ik 插件)，否则中文搜索搜不到东西。
* **索引管理**: 代码会自动检查并创建索引 (`pylab_cars_v1`)，无需手动创建。

### 3. 异步任务 (Celery)

* 主要用于“非核心业务”解耦，比如登录后发短信、风控分析等。
* **注意**: 现在的 ES 同步**不走** Celery 了，别去那里找同步逻辑。

---

## 🛠 快速启动

1. **环境准备**:
   **Bash**

   ```
   # 这里的 python 环境推荐 conda + uv
   uv pip install -r requirements.txt
   ```
2. **启动依赖 (Docker)**: 确保 PG(18+), Redis, RabbitMQ, Kafka, ES, Debezium 全家桶已就绪。
3. **跑起来**:
   **Bash**

   ```
   # 启动 API 服务
   python main.py

   # 启动 CDC 消费者 (同步数据的关键!)
   python -m app.consumers.cdc_sync
   ```
