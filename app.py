# -*- coding:utf-8 -*-
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint
from wordcloud import WordCloud
from io import BytesIO
import numpy as np
from PIL import Image
import os
import logging
import jieba
import re
from collections import Counter
import json
import random

# 初始化 Flask 应用
app = Flask(__name__)

# 配置日志系统
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# 处理静态文件路由
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# 配置 Swagger UI
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'
swagger_ui = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "词云生成 API"})
app.register_blueprint(swagger_ui, url_prefix=SWAGGER_URL)

# 加载停用词列表
def load_stopwords(filepath):
    stopwords = set()
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            stopwords.add(line.strip())
    return stopwords

stopwords = load_stopwords('stopwords.txt')

# 自定义随机颜色函数
def random_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    colors = [
        (255, 0, 0),    # 红
        (0, 255, 0),    # 绿
        (0, 0, 255),    # 蓝
        (255, 255, 0),  # 黄
        (255, 0, 255),  # 紫
        (0, 255, 255),  # 青
        (255, 165, 0),  # 橙
        (128, 0, 128),  # 深紫
    ]
    if random_state is not None:
        return colors[random_state.randint(0, len(colors) - 1)]
    return colors[random.randint(0, len(colors) - 1)]

# 获取随机遮罩文件路径
def get_random_mask():
    masks_dir = os.path.join(app.static_folder, 'masks')
    if not os.path.exists(masks_dir):
        app.logger.error(f"遮罩目录 {masks_dir} 不存在")
        return None
    mask_files = [f for f in os.listdir(masks_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not mask_files:
        app.logger.error(f"遮罩目录 {masks_dir} 中没有有效的图片文件")
        return None
    random_mask = os.path.join(masks_dir, random.choice(mask_files))
    app.logger.info(f"随机选择遮罩: {random_mask}")
    return random_mask

# 获取随机字体文件路径
def get_random_font():
    fonts_dir = os.path.join(app.static_folder, 'fonts')
    if not os.path.exists(fonts_dir):
        app.logger.error(f"字体目录 {fonts_dir} 不存在")
        return None
    font_files = [f for f in os.listdir(fonts_dir) if f.lower().endswith(('.ttf', '.ttc'))]
    if not font_files:
        app.logger.error(f"字体目录 {fonts_dir} 中没有有效的字体文件")
        return None
    random_font = os.path.join(fonts_dir, random.choice(font_files))
    app.logger.info(f"随机选择字体: {random_font}")
    return random_font

# 词云生成接口
@app.route('/generate_wordcloud', methods=['POST'])
def generate_wordcloud():
    try:
        if not request.is_json:
            return jsonify({"error": "请求必须是 application/json 格式"}), 400

        try:
            data = request.get_json(force=True, silent=False)
        except json.JSONDecodeError as e:
            app.logger.warning(f"JSON 解析错误: {str(e)}, 请求URL: {request.url}, 请求数据: {request.data}")
            return jsonify({"error": "无效的 JSON 数据"}), 400

        text = data.get('text', None)
        if not text or len(text) < 10:
            return jsonify({"error": "文本内容过短（至少需要10个字符）"}), 400

        # 清洗文本数据
        text = re.sub(r'[^\x20-\x7E\u4E00-\u9FFF]+', '', text)
        text = re.sub(r'[\r\n]+', ' ', text).strip()
        text = re.sub(r'[^\w\s]', '', text)

        # 获取随机字体
        font_path = get_random_font()
        if font_path is None:
            return jsonify({"error": "无法加载随机字体"}), 500

        # 定义画布尺寸
        canvas_width, canvas_height = 1600, 1600

        # 获取随机遮罩
        mask_path = get_random_mask()
        if mask_path is None:
            return jsonify({"error": "无法加载随机遮罩"}), 500

        mask_img = Image.open(mask_path).convert("L")  # 转换为灰度图
        mask = np.array(mask_img)
        app.logger.info(f"原始遮罩唯一值: {np.unique(mask)}")

        # 处理遮罩逻辑：黑色区域(<128)设为255，白色区域设为0
        mask = np.where(mask < 128, 255, 0).astype(np.uint8)
        app.logger.info(f"处理后遮罩唯一值: {np.unique(mask)}")

        # 调整遮罩尺寸与画布匹配
        if mask.shape != (canvas_height, canvas_width):
            mask_img = Image.fromarray(mask).resize((canvas_width, canvas_height), Image.LANCZOS)
            mask = np.array(mask_img)
            mask = np.where(mask > 128, 0, 255).astype(np.uint8)  # 重新应用二值化
            app.logger.info(f"调整尺寸后遮罩唯一值: {np.unique(mask)}")

        # 确保遮罩至少包含两种值
        unique_values = np.unique(mask)
        if len(unique_values) < 2:
            app.logger.warning("遮罩处理失败，全为单一值，反转尝试修正")
            mask = np.where(mask == 0, 255, 0).astype(np.uint8)
            app.logger.info(f"反转后遮罩唯一值: {np.unique(mask)}")

        # 保存处理后的遮罩用于调试
        Image.fromarray(mask).save("debug_mask_processed.png")

        # 使用 jieba 分词
        words = jieba.cut(text)
        filtered_words = [word for word in words if word not in stopwords and len(word) > 1]  # 过滤单字
        word_counts = Counter(filtered_words)
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)

        # 如果有效词太少，提示错误
        if len(filtered_words) < 5:
            return jsonify({"error": "有效词太少（少于5个），请提供更多文本"}), 400

        # 创建词云
        wordcloud = WordCloud(
            width=canvas_width,
            height=canvas_height,
            mask=mask,
            background_color="white",
            font_path=font_path,
            max_words=5000,
            color_func=random_color_func,
            min_font_size=10,
            max_font_size=80,
            contour_width=0,
            collocations=False,
            scale=3,
            random_state=42,
            prefer_horizontal=0.45
        ).generate_from_frequencies(dict(sorted_words))

        # 保存并返回词云
        img_buffer = BytesIO()
        wordcloud_img = wordcloud.to_image()
        #wordcloud_img.save("debug_wordcloud.png")  # 保存词云图片
        wordcloud_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        return send_file(img_buffer, mimetype='image/png')

    except ValueError as e:
        app.logger.warning(f"请求参数错误: {str(e)}, 请求URL: {request.url}, 请求参数: {request.json}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"服务器错误: {str(e)}, 请求URL: {request.url}, 请求参数: {request.json}")
        return jsonify({"error": "内部服务器错误"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)