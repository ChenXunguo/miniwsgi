# -*- coding: utf-8 -*-
"""
项目2 气温预测 API — MiniWSGI 版本。
使用本项目手写的 WSGI 框架替代 Flask，提供相同的预测接口。

运行：python examples/temp_predict_api.py
访问：http://127.0.0.1:8900

接口：
  GET  /health        健康检查
  GET  /model_info    模型元信息
  POST /predict       气温预测
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 项目2的路径（用于加载预测器和模型）
PROJECT2_PATH = r"C:\kunming_temp_prediction"
sys.path.insert(0, PROJECT2_PATH)

from miniwsgi import MiniWSGI, Response, BadRequest

app = MiniWSGI(debug=False)

# 懒加载预测器（首次请求时加载，避免启动慢）
_predictor = None


def get_predictor():
    global _predictor
    if _predictor is None:
        from src.predictor import load_predictor
        _predictor = load_predictor()
    return _predictor


@app.route("/health")
def health(request):
    """健康检查接口"""
    return Response.json({
        "status": "ok",
        "service": "kunming_daily_temp_predictor",
        "framework": "MiniWSGI (DIY WSGI Framework)",
    })


@app.route("/model_info")
def model_info(request):
    """模型元信息接口"""
    predictor = get_predictor()
    meta = predictor.metadata
    return Response.json({
        "model_type": meta.get("model_type", "RandomForest"),
        "feature_count": len(predictor.feature_names),
        "feature_names": predictor.feature_names,
        "test_mae": meta.get("test_mae"),
        "test_rmse": meta.get("test_rmse"),
        "test_r2": meta.get("test_r2"),
        "best_params": meta.get("best_params"),
        "train_period": meta.get("train_period"),
        "test_period": meta.get("test_period"),
    })


@app.route("/predict", methods=["POST"])
def predict(request):
    """
    气温预测接口。
    请求体 JSON：
    {
        "target_date": "2025-09-04",
        "recent_temps": [17.5, 17.9, 18.3, 18.5, 19.2, 20.1, 20.9, 21.5]
    }
    recent_temps：最近8天日均气温（含目标当日，按时间升序）
    """
    data = request.json
    if data is None:
        raise BadRequest("请求体必须是有效的 JSON")

    target_date = data.get("target_date")
    recent_temps = data.get("recent_temps")

    if not target_date or not recent_temps:
        raise BadRequest("缺少 target_date 或 recent_temps 参数")
    if len(recent_temps) != 8:
        raise BadRequest(f"recent_temps 需要8个值（含当日），实际 {len(recent_temps)} 个")

    predictor = get_predictor()
    result = predictor.predict(target_date, recent_temps)
    return Response.json({"ok": True, "result": result})


if __name__ == "__main__":
    print("=" * 50)
    print("昆明日均气温预测 API（MiniWSGI 版本）")
    print("=" * 50)
    app.list_routes()
    print()
    app.run(host="127.0.0.1", port=8900)
