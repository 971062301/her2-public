# her2 · 公开代码审查副本

这是“她2”的**代码审查副本**：只有代码，没有运行存档、日志、观测数据、API key。

- `her2/` 核心包
- `scripts/` 入口与实验脚本
- `tests.py` 全量测试

测试：

```powershell
$env:PYTHONPATH = "$PWD;$PWD\scripts"
python -X utf8 tests.py
```

设计说明和审计文档不在这个公开副本里；需要时另外提供。
