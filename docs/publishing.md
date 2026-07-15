# 发布 ormate

## 发布前检查

```bash
uv sync --all-extras
uv run ruff check .
uv run mypy
uv run pytest
uv build
uv run twine check dist/*
```

版本号必须同时更新 `pyproject.toml` 和 `CHANGELOG.md`。发布前确认 PyPI 上发行名仍可用。

## TestPyPI 验证

不要把令牌写入仓库。令牌通过环境变量或交互式提示提供。

```bash
uv publish --publish-url https://test.pypi.org/legacy/ dist/*
uv run --isolated --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ --with ormate python -c "import ormate; print(ormate.__all__)"
```

## PyPI 发布

TestPyPI 安装和冒烟验证通过后执行：

```bash
uv publish dist/*
```

长期维护建议在代码托管平台配置 PyPI Trusted Publishing，避免持久化 API Token。
