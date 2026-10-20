# PRD 智能体：从结构化需求录入到一致的交付物

> **Prototype，不用于生产。** 本仓库是原型参考实现，只用于非生产环境。上生产前需要加固的清单见
> [上生产前需要加固的清单](#上生产前需要加固的清单)。

发布时的建议仓库名：`prd-agent-requirements-to-deliverables`。

一线人员和产品经理按固定模板填写需求，模板生成一段确定性提示词；AI 编码智能体按编号知识库的顺序阅读后，
产出六份 IoT 产品交付物；最后由校验脚本确认这些交付物里的物模型 ID 一致。

| 交付物 | 格式 | 消费方 |
|---|---|---|
| 物模型 | `thing-model.json` | 云平台、设备端研发 |
| 产品架构图 | `architecture.mmd`（mermaid） | 评审 |
| 快速接入文档 | `quick-start.md` → `quick-start.pdf` | 外部开发者 |
| 需求规格说明书 / PRD | `PRD.md` | 产品、研发 |
| 面板交互说明与样式 | `panel-spec.md` + `panel-preview.html` | 面板 UI 设计 |
| 设备端 Demo 骨架 | `device-demo/`（C99） | 设备端研发 |

## 差异点

用 LLM 生成 PRD 的公开资产已经很多（检索结果见 [docs/prior-art.md](docs/prior-art.md)）。本项目多做了四件事：

1. **以物模型 ID 为主键做跨制品一致性校验**：`prd-agent validate` 从每份交付物的固定位置读出 ID、标识符和读写属性，有差异时逐条输出 `文件:行号`。
2. **编号知识库加读取顺序**：`AGENTS.md` 规定按 `knowledge-base/00` 到 `10` 的顺序阅读，规则在前，模板居中，案例最后。
3. **分段进度协议**：智能体在 10/25/45/70/90/100% 六个节点报告进度，每次都列出已产出的文件；`prd-agent check-progress` 拿这些清单和磁盘上的文件对照，能发现只搭了框架就结束的情况。
4. **输入不足先预警**：缺字段或字段互相矛盾时，先列出待确认项，提示词切换为 `CLARIFY_ONLY` 模式，不会猜测补全。

## 本地快速开始（不需要 AWS）

前置条件：Python 3.12+、[uv](https://docs.astral.sh/uv/)。Node.js 可选，只有 JS/Python 一致性测试需要。C 编译器可选，只有 Demo 骨架的编译测试需要。

```bash
uv sync
uv run pytest                                    # 单元测试

# 1. 录入：用浏览器直接打开 intake/pm.html 或 intake/frontline.html（可离线），或使用合成示例
uv run prd-agent check-intake sample-data/smart-plug.pm.intake.json
uv run prd-agent compile-prompt sample-data/smart-plug.pm.intake.json      # 人工复制到 AI 工具

# 2. 输入不足：列出待确认项，退出码 2，不生成任何文件
uv run prd-agent generate sample-data/smart-plug.missing-fields.intake.json --out out/missing

# 3. 本地参考生成器（智能体的模拟模式）：六份交付物加 PROGRESS.md
uv run prd-agent generate sample-data/smart-plug.pm.intake.json --out out/smart-plug

# 4. 校验（AI 智能体产出的目录也用同样的命令校验）
uv run prd-agent validate out/smart-plug
uv run prd-agent check-progress out/smart-plug
```

完整示例输出见 [`examples/smart-plug/`](examples/smart-plug/)，编译好的提示词见 [`examples/prompts/`](examples/prompts/)，演示步骤见 [docs/demo-script.md](docs/demo-script.md)。

### 配合 AI 编码智能体使用

用支持 `AGENTS.md` 的智能体打开本仓库作为工作区。例如 Kiro 会自动读取工作区根目录下的 `AGENTS.md`，依据见 [docs/architecture.md](docs/architecture.md#fact-check) 的事实核对。粘贴提示词并指定输出目录，完成后对该目录运行 `prd-agent validate` 和 `prd-agent check-progress`。

## 命令

| 命令 | 用途 |
|---|---|
| `check-intake <intake.json>` | 列出待确认项（有待确认项时退出码 2） |
| `compile-prompt <intake.json> [--out f]` | 生成确定性提示词文本 |
| `generate <intake.json> --out <dir>` | 本地参考生成器；有待确认项时拒绝生成（退出码 2），自身校验失败时退出码 1，I/O 或 PDF 错误时退出码 3（此时目标目录保持不变） |
| `validate <dir> [--format json] [--intake f]` | 以 ID 为主键的一致性校验。不带 `--intake` 时 FR-7 的文件必须存在 |
| `check-progress <dir> [--intake f]` | 进度协议校验 |
| `render-pdf <quick-start.md>` | Markdown 转 PDF |
| `diff-model <old.json> <new.json> [--fail-on-breaking]` | 物模型变更记录 |
| `build-forms` | 根据 schema 和系统提示词重新生成两个 HTML 录入页 |
| `publish <dir> --dest <目录或 s3://bucket/prefix> --name <bundle> [--intake f]` | 发布通过校验的交付物包；包名已存在时拒绝发布 |
| `fetch <src> --name <bundle> --out <dir>` | 下载交付物包并校验校验和 |

退出码：0 正常，1 校验失败，2 输入不足，3 用法或 I/O 错误。录入中请求的交付物少于 FR-7 的集合（PRD、快速接入文档、设备端骨架）时，加 `--intake` 参数。

## 可选的 AWS 部署

核心流程不需要 AWS。可选部署一个 CDK 栈，内容是一个私有、开启版本控制的 S3 桶（附带访问日志桶），用来存放发布的交付物包。栈里没有计算资源，也没有公网入口。

```bash
cd infra
npx -y aws-cdk@2 deploy -c config=config/sandbox.json
```

详见 [docs/deployment-guide.md](docs/deployment-guide.md) 和 [docs/cleanup.md](docs/cleanup.md)。计费维度为存储、请求和数据传输，价格以官方 [Amazon S3 定价页](https://aws.amazon.com/s3/pricing/) 为准。

## 清理

本地：删除 `out/` 目录。AWS：按 [docs/cleanup.md](docs/cleanup.md) 操作，先清空两个桶（包括所有对象版本），再执行 `cdk destroy`，最后做残留核对。

## 局限

- 不在线调用 AI。从录入台到 AI 工具之间是人工复制，这是刻意的取舍。
- 校验只比对 ID、标识符和读写属性，不比对取值范围和正文内容。可见文本只在使用 `knowledge-base/09` 中列出的固定格式时才校验（例如 ``ID 5 `timer_task` `` 和面板上的徽标），其他可见文本（如自由行文）不校验。
- 交付物使用英文，因为内置 PDF 字体只覆盖 Latin-1。请求快速接入文档时，进入 PDF 的字段如含 Latin-1 以外的字符，会列为待确认项。
- 面板只保证结构和 ID 映射正确，不保证视觉效果。
- 读取顺序靠 AGENTS.md 中的指令约束，工具本身不强制执行。
- 知识库只有一个合成案例（`knowledge-base/10-project-cases`）。用于其他产品类别前，需要先补充对应案例。
- 本项目没有效果数据，仓库中不声明任何效率或质量提升。

更多细节见 [docs/architecture.md](docs/architecture.md#limitations)。

## 上生产前需要加固的清单

详见 [docs/handover.md](docs/handover.md)。要点如下：
- 和实际团队一起评审知识库规则。
- 引入 Unicode 字体并审查其许可。
- 把 `validate` 和 `check-progress` 设为 CI 的合并门禁。
- 把桶的访问权限收紧到具名角色，开启数据保留，评估对制品桶改用 SSE-KMS。
- 对外文档发布前增加人工审核环节。

## 文档索引

[架构](docs/architecture.md) · [已有资产检索](docs/prior-art.md) · [部署](docs/deployment-guide.md) ·
[演示脚本](docs/demo-script.md) · [交接](docs/handover.md) · [清理](docs/cleanup.md) ·
[分发接口](docs/distribution.md) · [威胁模型](THREAT_MODEL.md) · [安全说明](SECURITY-NOTES.md) ·
[验证记录](VERIFICATION.md) · [部署记录](DEPLOYMENT-LOG.md) · [设计决策](DECISIONS.md) ·
[待确认问题](OPEN-QUESTIONS.md)

## 许可

MIT-0，见 [LICENSE](LICENSE)。
