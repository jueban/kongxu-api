# PKC-API
PKC自用API:
- 1.词云API
- 2.....

## Ⅰ.搭建PKC-API
### 方式一：Docker一键部署
```bash
docker run -d --name kx-api -p 80:80 juebanliaoshen/kx-api
```
支持修改词云背景图
路径：容器-目录-app-static下
background.png
![image](https://github.com/user-attachments/assets/d7135f1a-6d74-4539-bbb9-e0b7235233cd)


### 方式二：Docker-compose部署
建立文件`docker-compose.yaml`，文件内容以下：
```yaml
version: '3'
services:
  kx-api:
    image: juebanliaoshen/kx-api
    container_name: kx-api
    ports:
      - "8080:80"
    restart: unless-stopped
    volumes:
      - ./static:/app/static
```
启动
```bash
docker-compose up -d
```
## Ⅱ.Swagger API调试页面
```html
http://ip/swagger


```
![微信截图_20250303094327](https://github.com/user-attachments/assets/0d72aaf2-600b-4e7f-92bc-e8d776a990d2)

