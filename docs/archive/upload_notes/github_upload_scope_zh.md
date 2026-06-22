# GitHub 上传范围清单

本清单用于保护项目细节，避免上传时误删、误覆盖或误传本地环境。

## 原则

- 不删除本地任何实验数据、报告、图片、视频、CSV、checkpoint 或环境文件。
- GitHub 仓库优先展示可阅读、可复查、可引用的研究证据。
- 大型本地环境、训练输出和重复生成的二进制报告默认保留在本地，不进入 Git 版本库。
- 如果要补充到已有 GitHub 项目，先拉取/检查远程仓库，再只新增本项目文件，不覆盖远程已有内容。

## 建议上传

这些文件体现研究性和可复现性，建议进入 GitHub：

```text
README.md
pyproject.toml
.gitignore
src/
scripts/
tests/
docs/
reports/*.md
reports/tables/*.csv
reports/figures/**/*.png
reports/media/surrol_render_evidence/**/*.png
reports/media/surrol_render_evidence/**/*.gif
reports/media/surrol_render_evidence/**/*.mp4
```

## 本地保留但默认不上传

这些文件不删除，只是不建议作为首版 GitHub 仓库内容：

```text
.conda/
.conda_pkgs/
.pip_cache/
.pytest_cache/
runs/
*.zip
reports/*.docx
reports/*.pdf
reports/render_*/
reports/docx_audit_paths.txt
```

原因：

- `.conda/` 和缓存目录是本机环境，不适合上传。
- `runs/` 通常包含大量原始训练输出和 checkpoint，容易让仓库膨胀。
- docx/pdf 是 Markdown、CSV、figure 的重复编译版本；GitHub 上优先保留可 diff 的文本和结构化表格。
- `reports/render_*/` 是文档渲染中间产物，不是核心实验数据。
- `reports/docx_audit_paths.txt` 包含本机桌面路径，不适合公开上传。

## 当前首版 GitHub 重点

首版仓库应让导师快速看到：

1. 项目从 custom constrained 3D proxy 迁移到了 SurRoL。
2. 有 NeedleReach、NeedlePick、GauzeRetrieve 的渲染证据。
3. 有 10-seed recovery 结果，而不是只展示单次 demo。
4. 有 fault taxonomy。
5. 有 learned route classifier。
6. 有 observable supervisor，说明正在减少 privileged simulator-state dependence。
7. 限制声明清楚，不夸大成真实机器人或临床验证。

## 上传前必须检查

执行：

```powershell
git status --short
git status --ignored --short
```

确认：

- `.conda/`、`runs/` 没有出现在待提交文件里。
- `README.md`、`docs/`、`reports/tables/`、`reports/media/` 在待提交文件里。
- 没有密钥、账号、私人邮箱、无关压缩包。
- 如果是补充已有 GitHub 项目，不要使用会覆盖远程历史的命令，例如 `git push --force`。
