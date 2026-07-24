## 规范

- 项目以python -m 执行模块化执行，所以里面的依赖引用，请`import voyo.db.xx` 这种方式，而不是`import .db.xx`.
- 项目uv构建，启动python 使用uv，如`uv run python -m aa.bb`


## node.js

不需要编译ts， 新版的node.js 支持ts, 可直接运行。

## 测试

禁止mock!

## 构建项目文档

查看 `voyolibmcp/guide.md`