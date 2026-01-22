1.涉及到私人API的key一定要写到.env中(除非你喜欢当公交车让别人用你的钱)

2.非私人的公用key(数据库配置等)写到config.py

3.更新完依赖记得在左下角的python软件包刷新一下(conda比较笨,不会自己扫描)

项目结构:

```
carfast
	-app
		-core
		-models
		-schemas
		-services
		-tasks
		-utils
		-views
		-config.py
	-scripts
	-static
	-uploads
	-.env
	-main.py
	-requirements.txt
```

(1)core:存放全局服务(如es,rabbitmq)的连接与断开等代码

(2)models:存放模型类

(3)schemas:所有的接参入参参数

(4)services:各个服务(如es同步,数据转向量)的代码

(5)tasks:存放celery/rabbitmq任务

(6)utils:存放工具(如百度ocr,七牛云上传等)

(7)views:视图类

(8)config.py:所有的配置(包括无具体值的私密key)

(9).env:存放涉及隐私的具体配置信息
