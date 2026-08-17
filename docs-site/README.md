# ormate docs site

基于 Astro 7 与 Markdown Content Collections 的静态文档站，可直接部署到 Netlify。

## 本地预览

```bash
cd docs-site
npm install
npm run dev
```

访问 `http://localhost:4173`。

## Netlify 部署

将 Netlify 的 **Base directory** 设置为 `docs-site`：

- Build command：`npm run build`
- Publish directory：`dist`

也可以在 `docs-site` 目录执行 Netlify CLI：

```bash
npm run build
netlify deploy --dir dist
```
